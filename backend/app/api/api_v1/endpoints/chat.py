from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import re
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
from app.services.digital_human_client import get_client as get_dh_client
from app.services.digital_human_session import get_session_id
from app.database import get_db, SessionLocal
from app.models import Conversation, Message
from sqlalchemy import func

router = APIRouter()

TEMP_AUDIO_DIR = os.path.abspath(os.path.join("data", "temp_audios"))
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


async def _send_audio_to_livetalking(conversation_id: int, audio_filename: str):
    """将 TTS 生成的音频文件发送给 LiveTalking，驱动口型动画"""
    sessionid = get_session_id(conversation_id)
    if sessionid is None:
        return
    filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        await get_dh_client().send_audio(sessionid, audio_bytes)
    except Exception as e:
        print(f"[LiveTalking音频推送失败] conversation_id={conversation_id}: {e}")


def _split_sentences(text: str) -> list[str]:
    """按中文句号/感叹号/问号/换行拆分句子，过滤空串"""
    return [s for s in re.split(r'[。！？\n]+', text) if s.strip()]


# TTS Future 队列：合成并发执行，但播报按 LLM 生成顺序严格串行
_tts_queues: dict[int, asyncio.Queue] = {}


async def _tts_player(conversation_id: int, queue: asyncio.Queue):
    """顺序消费队列中的 TTS Future，逐句发送给 LiveTalking 播报"""
    try:
        while True:
            future = await queue.get()
            if future is None:
                break
            try:
                audio_filename = await future
                if not audio_filename:
                    continue
            except Exception as e:
                print(f"[TTS合成异常] conv={conversation_id}: {e}")
                continue
            try:
                await _send_audio_to_livetalking(conversation_id, audio_filename)
                filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
                file_size = os.path.getsize(filepath)
                duration = file_size / 5000 + 0.3
                await asyncio.sleep(duration)
            except Exception as e:
                print(f"[TTS播报失败] conv={conversation_id}: {e}")
    finally:
        _tts_queues.pop(conversation_id, None)


async def _enqueue_tts(conversation_id: int, text: str, queue: asyncio.Queue):
    """合成 TTS 并按 LLM 生成顺序入队；合成可并发，播报严格保序"""
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    await queue.put(future)
    try:
        audio_filename = await synthesize_to_file(text, TEMP_AUDIO_DIR)
        future.set_result(audio_filename if audio_filename else None)
    except Exception as e:
        print(f"[逐句TTS合成失败] conv={conversation_id}: {e}")
        future.set_result(None)


class ChatTextRequest(BaseModel):
    conversation_id: int
    content: str
    response_type: int = 1
    digital_human_id: int = 0


class SimpleChatRequest(BaseModel):
    question: str


@router.post("/chat/stream")
async def stream_chat(req: ChatTextRequest):
    """流式文本问答，逐 token 返回 SSE 事件"""
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
        prompt = build_prompt(req.content, context_list)

        async def event_generator():
            full_content = ""
            sentence_buffer = ""
            queue = asyncio.Queue()
            _tts_queues[req.conversation_id] = queue
            player_task = asyncio.create_task(_tts_player(req.conversation_id, queue))

            try:
                async for token in generate_stream_async(
                    [{"role": "user", "content": prompt}]
                ):
                    full_content += token
                    sentence_buffer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

                    if sentence_buffer and sentence_buffer[-1] in "。！？\n":
                        sentences = _split_sentences(sentence_buffer)
                        for s in sentences:
                            if req.response_type == 1:
                                asyncio.create_task(
                                    _enqueue_tts(req.conversation_id, s, queue)
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
                    asyncio.create_task(
                        _enqueue_tts(req.conversation_id, s, queue)
                    )
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
                        # 逐句TTS已发送音频到LiveTalking，此处仅生成audio_url供数据库存储和AudioPlayer回退
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
                await _send_audio_to_livetalking(req.conversation_id, audio_filename)
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


@router.post("/chat")
def handle_text_chat(request: SimpleChatRequest):
    """纯文本问答（简单版，无持久化，用于快速测试）"""
    user_text = request.question
    print(f"收到文本提问：{user_text}")

    context_list = retrieve_context(user_text)
    prompt = build_prompt(user_text, context_list)
    answer_text = generate(prompt)

    return {"status": "success", "question": user_text, "answer": answer_text}


# 接口 2：语音问答闭环接口 (ASR -> RAG -> LLM -> TTS)


@router.post("/chat_voice")
async def handle_voice_chat(audio_file: UploadFile = File(...)):
    """处理前端录音文件，返回解答文字和生成的语音音频"""

    input_audio_path = os.path.join(TEMP_AUDIO_DIR, f"in_{time.time()}.wav")
    with open(input_audio_path, "wb") as f:
        f.write(await audio_file.read())

    user_text = await asyncio.to_thread(transcribe_audio, input_audio_path)
    print(f"游客语音识别结果：{user_text}")

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


@router.post("/chat/voice_stream")
async def handle_voice_stream(
    audio: UploadFile = File(...),
    conversation_id: int = Form(...),
    digital_human_id: int = Form(0),
    response_type: int = Form(1),
):
    """语音流式问答：上传音频 → ASR识别 → 流式返回识别文本 + LLM回复"""
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
            queue = asyncio.Queue()
            _tts_queues[conversation_id] = queue
            player_task = asyncio.create_task(_tts_player(conversation_id, queue))
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
                prompt_text = build_prompt(user_text, context_list)

                async for token in generate_stream_async(
                    [{"role": "user", "content": prompt_text}]
                ):
                    full_content += token
                    sentence_buffer += token
                    yield f"data: {json.dumps({'type': 'token', 'conversation_id': conversation_id, 'content': token}, ensure_ascii=False)}\n\n"

                    if sentence_buffer and sentence_buffer[-1] in "。！？\n":
                        sentences = _split_sentences(sentence_buffer)
                        for s in sentences:
                            if response_type == 1:
                                asyncio.create_task(
                                    _enqueue_tts(conversation_id, s, queue)
                                )
                            yield f"data: {json.dumps({'type': 'sentence', 'conversation_id': conversation_id, 'content': s}, ensure_ascii=False)}\n\n"
                        sentence_buffer = ""

                # 处理缓冲区中剩余文本
                if sentence_buffer.strip():
                    s = sentence_buffer.strip()
                    if response_type == 1:
                        asyncio.create_task(
                            _enqueue_tts(conversation_id, s, queue)
                        )
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


# 接口 3：配套的音频下载接口 (供前端播放使用)
@router.get("/download_audio")
def download_audio(filename: str):
    """前端拿到 audio_url 后，调用这个接口获取真实的 mp3 文件"""
    file_path = os.path.join(TEMP_AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "音频文件找不到了"}
    return FileResponse(file_path, media_type="audio/mpeg")
