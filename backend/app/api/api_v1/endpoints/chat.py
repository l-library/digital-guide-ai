from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import time
import json

from app.services.rag_service import retrieve_context, build_prompt
from app.services.llm_service import generate, generate_stream_async, generate_title_async
from app.database import get_db, SessionLocal
from app.models import Conversation, Message
from sqlalchemy import func
# 这部分之后可能要用到，现在还没做好
# from app.services.asr_service import transcribe_audio
# from app.services.tts_service import synthesize_audio

router = APIRouter()

TEMP_AUDIO_DIR = "data/temp_audios"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


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
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
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
            try:
                async for token in generate_stream_async([{"role": "user", "content": prompt}]):
                    full_content += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
                db.rollback()
                db.close()
                return

            assistant_msg = Message(
                conversation_id=req.conversation_id,
                role="assistant",
                content=full_content,
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(assistant_msg)

            yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id, 'full_content': full_content, 'knowledge_sources': ['景区知识库'] if context_list else []}, ensure_ascii=False)}\n\n"

            # 第一轮对话结束后自动生成标题
            msg_count = db.query(func.count(Message.id)).filter(
                Message.conversation_id == req.conversation_id
            ).scalar()
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
async def handle_text_chat_with_persistence(req: ChatTextRequest, db: Session = Depends(get_db)):
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

    assistant_msg = Message(
        conversation_id=req.conversation_id,
        role="assistant",
        content=answer_text,
    )
    db.add(assistant_msg)
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)

    # 第一轮对话结束后自动生成标题
    msg_count = db.query(func.count(Message.id)).filter(
        Message.conversation_id == req.conversation_id
    ).scalar()
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
            "audio_url": None,
            "knowledge_sources": ["景区知识库"] if context_list else [],
            "title_updated": title_updated,
        }
    }


@router.post("/chat")
def handle_text_chat(request: SimpleChatRequest):
    """纯文本问答（简单版，无持久化，用于快速测试）"""
    user_text = request.question
    print(f"收到文本提问：{user_text}")

    context_list = retrieve_context(user_text)
    prompt = build_prompt(user_text, context_list)
    answer_text = generate(prompt)

    return {
        "status": "success",
        "question": user_text,
        "answer": answer_text
    }


# 接口 2：语音问答闭环接口 (ASR -> RAG -> LLM -> TTS)

@router.post("/chat_voice")
async def handle_voice_chat(audio_file: UploadFile = File(...)):
    """处理前端录音文件，返回解答文字和生成的语音音频"""
    
    # 1. 存音频：把前端传来的语音包裹暂存到本地
    input_audio_path = os.path.join(TEMP_AUDIO_DIR, f"in_{time.time()}.wav")
    with open(input_audio_path, "wb") as f:
        f.write(await audio_file.read())
        
    # 2. ASR
    user_text = transcribe_audio(input_audio_path)
    print(f"游客语音识别结果：{user_text}")
    
    # 3. RAG + LLM
    context_list = retrieve_context(user_text)
    prompt = build_prompt(user_text, context_list)
    answer_text = generate(prompt)
    print(f"数字人回复生成：{answer_text}")
    
    # 4. TTS
    output_audio_path = os.path.join(TEMP_AUDIO_DIR, f"out_{time.time()}.mp3")
    await synthesize_audio(answer_text, output_audio_path)
    
    # 5. 把答案和音频下载链接发给前端
    return {
        "status": "success",
        "question": user_text,
        "answer": answer_text,
        "audio_url": f"/api/v1/download_audio?filename={os.path.basename(output_audio_path)}"
    }


# 接口 3：配套的音频下载接口 (供前端播放使用)
@router.get("/download_audio")
def download_audio(filename: str):
    """前端拿到 audio_url 后，调用这个接口获取真实的 mp3 文件"""
    file_path = os.path.join(TEMP_AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "音频文件找不到了"}
    return FileResponse(file_path, media_type="audio/mpeg")