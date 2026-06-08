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
    generate_stream_async,
    generate_title_async,
)
from app.services.asr_service import transcribe_audio
from app.services.tts_service import synthesize_to_file
from app.services.tts_streaming import (
    split_sentences,
    send_audio_to_livetalking,
    synthesize_and_resolve,
    enqueue_tts_sync,
    create_tts_queue,
    TEMP_AUDIO_DIR,
)
from app.database import get_db, SessionLocal
from app.models import Conversation, Message
from sqlalchemy import func

router = APIRouter()


class ChatTextRequest(BaseModel):
    conversation_id: int
    content: str
    response_type: int = 1
    digital_human_id: int = 0


class SimpleChatRequest(BaseModel):
    question: str


# ─── 构建多轮对话消息列表的工具函数 ────────────────────────────────────────────


def _build_llm_messages(
    history_msgs: list,
    user_query: str,
    context_list: list[str],
) -> list[dict]:
    """根据对话历史构建发送给 LLM 的消息列表。
    首轮对话（≤2条消息）使用完整 RAG prompt，
    多轮对话使用 system message + 上下文 + 完整历史。
    """
    messages = [{"role": m.role, "content": m.content} for m in history_msgs]

    if len(messages) <= 2:
        prompt = build_prompt(user_query, context_list)
        return [{"role": "user", "content": prompt}]

    system_msg = {
        "role": "system",
        "content": (
            "你是一名经验丰富的景区导游。作为一名导游，你需要为用户提供丰富、有趣的旅行体验。"
            "核心技能：丰富的旅游知识储备、出色的沟通和表达能力、创意思维和创新能力"
            "你的工作准则是提供准确、可靠的旅游信息、尊重不同文化和地区的习俗、以用户为中心，满足个性化需求"
            "工作流程：了解用户需求和偏好、引导用户说出自己的需求、提供详细解说和互动、收集用户反馈，持续优化体验"
            "沟通风格：保持热情、友好、幽默的态度，让用户感受到愉快的虚拟旅游体验。"
            "价值观：尊重文化多样性、提供真实、有价值的旅游信息、注重用户体验，满足个性化需求"
            "语气自然亲切。不要使用emoji或动作描写。"
            "如果资料中没有相关信息，请如实告知。"
        ),
    }
    context_msg = {
        "role": "system",
        "content": f"参考景区资料：\n{chr(10).join(context_list)}",
    }
    history_without_last = messages[:-1]
    last_user_msg = messages[-1]
    return [system_msg, context_msg] + history_without_last + [last_user_msg]


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
            full_content = ""
            sentence_buffer = ""
            stream_id, queue, player_task = create_tts_queue(req.conversation_id)

            try:
                # 加载对话历史（含刚保存的用户消息），构建多轮消息列表
                history_msgs = (
                    db.query(Message)
                    .filter(Message.conversation_id == req.conversation_id)
                    .order_by(Message.created_at)
                    .all()
                )
                messages_for_llm = _build_llm_messages(
                    history_msgs, req.content, context_list
                )

                async for token in generate_stream_async(messages_for_llm):
                    full_content += token
                    sentence_buffer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

                    if sentence_buffer and sentence_buffer[-1] in "。！？\n":
                        sentences = split_sentences(sentence_buffer)
                        for s in sentences:
                            if req.response_type == 1:
                                future = enqueue_tts_sync(s, queue)
                                asyncio.create_task(
                                    synthesize_and_resolve(s, future)
                                )
                            yield f"data: {json.dumps({'type': 'sentence', 'conversation_id': req.conversation_id, 'content': s}, ensure_ascii=False)}\n\n"
                        sentence_buffer = ""

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
                if req.response_type == 1:
                    await queue.put(None)
                db.rollback()
                db.close()
                return

            # 处理缓冲区中剩余文本
            if sentence_buffer.strip():
                s = sentence_buffer.strip()
                if req.response_type == 1:
                    future = enqueue_tts_sync(s, queue)
                    asyncio.create_task(synthesize_and_resolve(s, future))
                yield f"data: {json.dumps({'type': 'sentence', 'conversation_id': req.conversation_id, 'content': s}, ensure_ascii=False)}\n\n"

            if req.response_type == 1:
                await queue.put(None)

            audio_url = None
            if req.response_type == 1:
                try:
                    audio_filename = await synthesize_to_file(
                        full_content, TEMP_AUDIO_DIR
                    )
                    if audio_filename:
                        audio_url = f"/api/v1/download_audio?filename={audio_filename}"
                except Exception as e:
                    print(f"[TTS失败] {e}")

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

            yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id, 'full_content': full_content, 'knowledge_sources': ['景区知识库'] if context_list else [], 'audio_url': audio_url}, ensure_ascii=False)}\n\n"

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
async def handle_voice_chat(audio_file: UploadFile = File(...)):
    """处理前端录音文件，返回解答文字和生成的语音音频"""

    input_audio_path = os.path.join(TEMP_AUDIO_DIR, f"in_{time.time()}.wav")
    try:
        with open(input_audio_path, "wb") as f:
            f.write(await audio_file.read())

        user_text = await asyncio.to_thread(transcribe_audio, input_audio_path)
        print(f"游客语音识别结果：{user_text}")

        # 检查 ASR 是否失败，避免将错误信息传给 RAG/LLM
        if user_text.startswith("语音识别失败:"):
            return {"status": "error", "message": user_text}

        context_list = retrieve_context(user_text)
        prompt = build_prompt(user_text, context_list)
        answer_text = generate(prompt)
        print(f"数字人回复生成：{answer_text}")

        audio_url = None
        try:
            audio_filename = await synthesize_to_file(answer_text, TEMP_AUDIO_DIR)
            if audio_filename:
                audio_url = f"/api/v1/download_audio?filename={audio_filename}"
        except Exception as e:
            print(f"[TTS失败] {e}")

        return {
            "status": "success",
            "question": user_text,
            "answer": answer_text,
            "audio_url": audio_url,
        }
    finally:
        try:
            os.remove(input_audio_path)
        except OSError:
            pass


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
            full_content = ""
            sentence_buffer = ""
            stream_id, queue, player_task = create_tts_queue(conversation_id)
            try:
                user_text = await asyncio.to_thread(transcribe_audio, input_audio_path)
                print(f"[voice_stream] 识别结果：{user_text}")

                if user_text.startswith("语音识别失败:"):
                    yield f"data: {json.dumps({'type': 'error', 'conversation_id': conversation_id, 'message': user_text}, ensure_ascii=False)}\n\n"
                    if response_type == 1:
                        await queue.put(None)
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
                messages_for_llm = _build_llm_messages(
                    history_msgs, user_text, context_list
                )

                async for token in generate_stream_async(messages_for_llm):
                    full_content += token
                    sentence_buffer += token
                    yield f"data: {json.dumps({'type': 'token', 'conversation_id': conversation_id, 'content': token}, ensure_ascii=False)}\n\n"

                    if sentence_buffer and sentence_buffer[-1] in "。！？\n":
                        sentences = split_sentences(sentence_buffer)
                        for s in sentences:
                            if response_type == 1:
                                future = enqueue_tts_sync(s, queue)
                                asyncio.create_task(
                                    synthesize_and_resolve(s, future)
                                )
                            yield f"data: {json.dumps({'type': 'sentence', 'conversation_id': conversation_id, 'content': s}, ensure_ascii=False)}\n\n"
                        sentence_buffer = ""

                # 处理缓冲区中剩余文本
                if sentence_buffer.strip():
                    s = sentence_buffer.strip()
                    if response_type == 1:
                        future = enqueue_tts_sync(s, queue)
                        asyncio.create_task(synthesize_and_resolve(s, future))
                    yield f"data: {json.dumps({'type': 'sentence', 'conversation_id': conversation_id, 'content': s}, ensure_ascii=False)}\n\n"

                if response_type == 1:
                    await queue.put(None)

                audio_url = None
                if response_type == 1:
                    try:
                        audio_filename = await synthesize_to_file(
                            full_content, TEMP_AUDIO_DIR
                        )
                        if audio_filename:
                            audio_url = (
                                f"/api/v1/download_audio?filename={audio_filename}"
                            )
                    except Exception as e:
                        print(f"[TTS失败] {e}")

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

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'conversation_id': conversation_id, 'message': f'服务器错误: {str(e)}'}, ensure_ascii=False)}\n\n"
                if response_type == 1:
                    await queue.put(None)
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
