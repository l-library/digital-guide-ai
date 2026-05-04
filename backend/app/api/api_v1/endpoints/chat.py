from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import time

from app.services.rag_service import retrieve_context, build_prompt
from app.services.llm_service import generate
from app.database import get_db
from app.models import Conversation, Message
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


@router.post("/chat/text")
def handle_text_chat_with_persistence(req: ChatTextRequest, db: Session = Depends(get_db)):
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
    db.commit()
    db.refresh(assistant_msg)

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