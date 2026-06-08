from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import time
import json
import asyncio

from app.services.rag_service import retrieve_context, build_prompt
from app.services.llm_service import (
    generate,
    generate_title_async,
)
from app.services.asr_service import transcribe_audio
from app.services.tts_service import synthesize_to_file
from app.services.tts_streaming import (
    create_streaming_pipeline,
    send_audio_to_livetalking,
    TEMP_AUDIO_DIR,
)
from app.database import get_db, SessionLocal
from app.models import Conversation, Message
from app.services.streaming_utils import build_llm_messages
from sqlalchemy import func

router = APIRouter()


class ChatTextRequest(BaseModel):
    conversation_id: int
    content: str
    response_type: int = 1
    digital_human_id: int = 0


class SimpleChatRequest(BaseModel):
    question: str



# ─── 流式文本问答 ──────────────────────────────────────────────────────────────


@router.post("/chat/stream")
async def stream_chat(req: ChatTextRequest):
    """流式文本问答，逐 token 返回 SSE 事件，支持多轮对话历史"""
    db = SessionLocal()
    try:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == req.conversation_id)
            .first()
        )
        if not conv:
            db.close()
            return {"code": 404, "message": "对话不存在", "data": {}}

        user_msg = Message(
            conversation_id=req.conversation_id,
            role="user",
            content=req.content,
        )
        db.add(user_msg)
        db.commit()

        context_list = retrieve_context(req.content)

        async def event_generator():
            try:
                # 加载对话历史（含刚保存的用户消息），构建多轮消息列表
                history_msgs = (
                    db.query(Message)
                    .filter(Message.conversation_id == req.conversation_id)
                    .order_by(Message.created_at)
                    .all()
                )
                messages_for_llm = build_llm_messages(
                    history_msgs, req.content, context_list
                )

                pipeline = create_streaming_pipeline(
                    req.conversation_id, req.response_type, messages_for_llm
                )
                async for event in pipeline:
                    if event["type"] == "_pipeline_done":
                        full_content = event["full_content"]
                        break
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            except Exception:
                db.rollback()
                db.close()
                return

            audio_url = None

            assistant_msg = Message(
                conversation_id=req.conversation_id,
                role="assistant",
                content=full_content,
                audio_url=audio_url,
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_msg)

            yield f"data: {json.dumps({'type': 'done', 'conversation_id': req.conversation_id, 'message_id': assistant_msg.id, 'full_content': full_content, 'knowledge_sources': ['景区知识库'] if context_list else [], 'audio_url': audio_url}, ensure_ascii=False)}\n\n"

            # 第一轮对话结束后自动生成标题
            msg_count = (
                db.query(func.count(Message.id))
                .filter(Message.conversation_id == req.conversation_id)
                .scalar()
            )
            if msg_count <= 2:
                try:
                    title = await generate_title_async(req.content, full_content)
                    conv.title = title
                    db.commit()
                    yield f"data: {json.dumps({'type': 'title_updated', 'conversation_id': req.conversation_id, 'title': title}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    print(f"[标题生成失败] conversation_id={req.conversation_id}: {e}")

            db.close()

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception:
        db.close()
        raise


# ─── 非流式文本问答 ────────────────────────────────────────────────────────────


@router.post("/chat/text")
async def handle_text_chat_with_persistence(
    req: ChatTextRequest, db: Session = Depends(get_db)
):
    user_text = req.content
    print(f"收到文本提问（对话{req.conversation_id}）：{user_text}")

    conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
    if not conv:
        return {"code": 404, "message": "对话不存在", "data": {}}

    user_msg = Message(
        conversation_id=req.conversation_id,
        role="user",
        content=user_text,
    )
    db.add(user_msg)
    db.commit()

    context_list = retrieve_context(user_text)
    prompt = build_prompt(user_text, context_list)
    answer_text = generate(prompt)

    audio_url = None
    if req.response_type == 1:
        try:
            audio_filename = await synthesize_to_file(answer_text, TEMP_AUDIO_DIR)
            if audio_filename:
                audio_url = f"/api/v1/download_audio?filename={audio_filename}"
                await send_audio_to_livetalking(
                    req.conversation_id, audio_filename
                )
        except Exception as e:
            print(f"[TTS失败] {e}")

    assistant_msg = Message(
        conversation_id=req.conversation_id,
        role="assistant",
        content=answer_text,
        audio_url=audio_url,
    )
    db.add(assistant_msg)
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)

    # 第一轮对话结束后自动生成标题
    msg_count = (
        db.query(func.count(Message.id))
        .filter(Message.conversation_id == req.conversation_id)
        .scalar()
    )
    title_updated = None
    if msg_count <= 2:
        try:
            title = await generate_title_async(user_text, answer_text)
            conv.title = title
            db.commit()
            title_updated = title
        except Exception as e:
            print(f"[标题生成失败] conversation_id={req.conversation_id}: {e}")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "conversation_id": req.conversation_id,
            "message_id": assistant_msg.id,
            "role": "assistant",
            "content": answer_text,
            "audio_url": audio_url,
            "knowledge_sources": ["景区知识库"] if context_list else [],
            "title_updated": title_updated,
        },
    }


# ─── 纯文本问答（简单版，无持久化）─────────────────────────────────────────────


@router.post("/chat")
def handle_text_chat(request: SimpleChatRequest):
    """纯文本问答（简单版，无持久化，用于快速测试）"""
    user_text = request.question
    print(f"收到文本提问：{user_text}")

    context_list = retrieve_context(user_text)
    prompt = build_prompt(user_text, context_list)
    answer_text = generate(prompt)

    return {"status": "success", "question": user_text, "answer": answer_text}


# ─── 语音问答 ─────────────────────────────────────────────────────────────────


@router.post("/chat_voice")
async def handle_voice_chat(
    audio_file: UploadFile = File(...),
    conversation_id: int = Form(...),
    response_type: int = Form(1),
    digital_human_id: int = Form(0),
):
    """语音流式问答：上传音频 → ASR识别 → 流式返回识别文本 + LLM回复，多轮对话历史"""
    db = SessionLocal()
    try:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not conv:
            db.close()
            return {"code": 404, "message": "对话不存在", "data": {}}

        audio_bytes = await audio_file.read()
        audio_ext = os.path.splitext(audio_file.filename or ".wav")[1] or ".wav"
        input_audio_path = os.path.join(
            TEMP_AUDIO_DIR, f"voice_in_{time.time()}{audio_ext}"
        )
        with open(input_audio_path, "wb") as f:
            f.write(audio_bytes)

        async def event_generator():
            try:
                user_text = await asyncio.to_thread(transcribe_audio, input_audio_path)
                print(f"[chat_voice] 识别结果：{user_text}")

                if user_text.startswith("语音识别失败:"):
                    yield f"data: {json.dumps({'type': 'error', 'conversation_id': conversation_id, 'message': user_text}, ensure_ascii=False)}\n\n"
                    db.close()
                    return

                yield f"data: {json.dumps({'type': 'transcribed_text', 'conversation_id': conversation_id, 'content': user_text}, ensure_ascii=False)}\n\n"

                user_msg = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_text,
                )
                db.add(user_msg)
                db.commit()

                context_list = retrieve_context(user_text)

                # 加载对话历史（含刚保存的用户消息），构建多轮消息列表
                history_msgs = (
                    db.query(Message)
                    .filter(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                    .all()
                )
                messages_for_llm = build_llm_messages(
                    history_msgs, user_text, context_list
                )

                pipeline = create_streaming_pipeline(
                    conversation_id, response_type, messages_for_llm
                )
                async for event in pipeline:
                    if event["type"] == "_pipeline_done":
                        full_content = event["full_content"]
                        break
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                audio_url = None

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                    audio_url=audio_url,
                )
                db.add(assistant_msg)
                conv.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(assistant_msg)

                knowledge_sources = ["景区知识库"] if context_list else []

                yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'message_id': assistant_msg.id, 'full_content': full_content, 'knowledge_sources': knowledge_sources, 'audio_url': audio_url}, ensure_ascii=False)}\n\n"

                # 第一轮对话结束后自动生成标题
                msg_count = (
                    db.query(func.count(Message.id))
                    .filter(Message.conversation_id == conversation_id)
                    .scalar()
                )
                if msg_count <= 2:
                    try:
                        title = await generate_title_async(user_text, full_content)
                        conv.title = title
                        db.commit()
                        yield f"data: {json.dumps({'type': 'title_updated', 'conversation_id': conversation_id, 'title': title}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        print(f"[标题生成失败] conversation_id={conversation_id}: {e}")

            except Exception:
                db.rollback()
            finally:
                try:
                    os.remove(input_audio_path)
                except OSError:
                    pass
                db.close()

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception:
        db.close()
        raise


# ─── 语音流式问答 ─────────────────────────────────────────────────────────────


@router.post("/chat/voice_stream")
async def handle_voice_stream(
    audio: UploadFile = File(...),
    conversation_id: int = Form(...),
    digital_human_id: int = Form(0),
    response_type: int = Form(1),
):
    """语音流式问答：上传音频 → ASR识别 → 流式返回识别文本 + LLM回复，支持多轮对话历史"""
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            db.close()
            return {"code": 404, "message": "对话不存在", "data": {}}

        audio_bytes = await audio.read()
        audio_ext = os.path.splitext(audio.filename or ".wav")[1] or ".wav"
        input_audio_path = os.path.join(
            TEMP_AUDIO_DIR, f"voice_in_{time.time()}{audio_ext}"
        )
        with open(input_audio_path, "wb") as f:
            f.write(audio_bytes)

        async def event_generator():
            try:
                user_text = await asyncio.to_thread(transcribe_audio, input_audio_path)
                print(f"[voice_stream] 识别结果：{user_text}")

                if user_text.startswith("语音识别失败:"):
                    yield f"data: {json.dumps({'type': 'error', 'conversation_id': conversation_id, 'message': user_text}, ensure_ascii=False)}\n\n"
                    db.close()
                    return

                yield f"data: {json.dumps({'type': 'transcribed_text', 'conversation_id': conversation_id, 'content': user_text}, ensure_ascii=False)}\n\n"

                user_msg = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_text,
                )
                db.add(user_msg)
                db.commit()

                context_list = retrieve_context(user_text)

                # 加载对话历史（含刚保存的用户消息），构建多轮消息列表
                history_msgs = (
                    db.query(Message)
                    .filter(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                    .all()
                )
                messages_for_llm = build_llm_messages(
                    history_msgs, user_text, context_list
                )

                pipeline = create_streaming_pipeline(
                    conversation_id, response_type, messages_for_llm
                )
                async for event in pipeline:
                    if event["type"] == "_pipeline_done":
                        full_content = event["full_content"]
                        break
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                audio_url = None

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                    audio_url=audio_url,
                )
                db.add(assistant_msg)
                conv.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(assistant_msg)

                knowledge_sources = ["景区知识库"] if context_list else []

                yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'message_id': assistant_msg.id, 'full_content': full_content, 'knowledge_sources': knowledge_sources, 'audio_url': audio_url}, ensure_ascii=False)}\n\n"

                # 自动标题：首轮对话后生成
                msg_count = (
                    db.query(func.count(Message.id))
                    .filter(Message.conversation_id == conversation_id)
                    .scalar()
                )
                if msg_count <= 2:
                    try:
                        title = await generate_title_async(user_text, full_content)
                        conv.title = title
                        db.commit()
                        yield f"data: {json.dumps({'type': 'title_updated', 'conversation_id': conversation_id, 'title': title}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        print(f"[标题生成失败] conversation_id={conversation_id}: {e}")

            except Exception:
                db.rollback()
            finally:
                try:
                    os.remove(input_audio_path)
                except OSError:
                    pass
                db.close()

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception:
        db.close()
        raise


# ─── 音频下载 ─────────────────────────────────────────────────────────────────


@router.get("/download_audio")
def download_audio(filename: str):
    """前端拿到 audio_url 后，调用这个接口获取真实的 wav 文件"""
    file_path = os.path.join(TEMP_AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "音频文件找不到了"}
    return FileResponse(file_path, media_type="audio/wav")
