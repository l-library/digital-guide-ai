"""数字人交互接口：会话管理、播报、打断、状态查询。"""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.digital_human_client import get_client
from app.services.digital_human_session import (
    create_digital_human_session,
    destroy_session,
    get_session_id,
    register_session,
)

router = APIRouter()


class CreateSessionRequest(BaseModel):
    conversation_id: int
    avatar: str | None = None


class RegisterSessionRequest(BaseModel):
    conversation_id: int
    session_id: str


class SpeakRequest(BaseModel):
    conversation_id: int
    text: str


class InterruptRequest(BaseModel):
    conversation_id: int


class PlayAudioRequest(BaseModel):
    conversation_id: int
    audio_filename: str


@router.post("/session")
async def create_session(req: CreateSessionRequest):
    """为 conversation_id 创建数字人会话。"""
    try:
        sessionid = await create_digital_human_session(req.conversation_id)
    except httpx.HTTPError:
        return {"code": 500, "message": "数字人服务连接失败"}
    except RuntimeError:
        return {"code": 500, "message": "数字人服务返回异常"}
    return {
        "code": 200,
        "message": "success",
        "data": {"session_id": sessionid, "conversation_id": req.conversation_id},
    }


@router.delete("/session/{conversation_id}")
async def delete_session(conversation_id: int):
    """销毁数字人会话。"""
    try:
        destroyed = await destroy_session(conversation_id)
    except httpx.HTTPError:
        return {"code": 500, "message": "数字人服务连接失败"}
    if not destroyed:
        return {"code": 404, "message": "会话不存在"}
    return {"code": 200, "message": "success"}


@router.post("/register_session")
async def register_session_endpoint(req: RegisterSessionRequest):
    """注册前端已创建的 LiveTalking sessionid 到 conversation_id 映射"""
    register_session(req.conversation_id, req.session_id)
    return {"code": 200, "message": "success"}


@router.post("/speak")
async def speak(req: SpeakRequest):
    """驱动数字人播报文本。"""
    sessionid = get_session_id(req.conversation_id)
    if sessionid is None:
        return {"code": 404, "message": "会话不存在"}
    try:
        await get_client().speak(sessionid, req.text)
    except httpx.HTTPError:
        return {"code": 500, "message": "数字人服务连接失败"}
    return {"code": 200, "message": "success"}


@router.post("/interrupt")
async def interrupt(req: InterruptRequest):
    """打断当前播报。"""
    sessionid = get_session_id(req.conversation_id)
    if sessionid is None:
        return {"code": 404, "message": "会话不存在"}
    try:
        await get_client().interrupt(sessionid)
    except httpx.HTTPError:
        return {"code": 500, "message": "数字人服务连接失败"}
    return {"code": 200, "message": "success"}


@router.post("/play-audio")
async def play_audio(req: PlayAudioRequest):
    """前端调用，将指定 WAV 发送给 LiveTalking 驱动口型动画。

    前端逐句调用此端点，播放顺序由前端 QTimer 控制。
    """
    import time

    t0 = time.monotonic()
    from app.services.tts_streaming import send_audio_to_livetalking
    await send_audio_to_livetalking(req.conversation_id, req.audio_filename)
    elapsed = time.monotonic() - t0
    print(f"[play-audio] conv={req.conversation_id} file={req.audio_filename} 总耗时={elapsed:.3f}s")
    return {"code": 200, "message": "ok"}


@router.get("/status/{conversation_id}")
async def get_status(conversation_id: int):
    """查询数字人是否正在说话。"""
    sessionid = get_session_id(conversation_id)
    if sessionid is None:
        return {"code": 404, "message": "会话不存在"}
    try:
        is_speaking = await get_client().is_speaking(sessionid)
    except httpx.HTTPError:
        return {"code": 500, "message": "数字人服务连接失败"}
    return {"code": 200, "message": "success", "data": {"is_speaking": is_speaking}}