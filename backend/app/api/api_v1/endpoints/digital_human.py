"""数字人交互接口：会话管理、播报、打断、状态查询。"""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.digital_human_client import get_client
from app.services.digital_human_session import (
    create_digital_human_session,
    destroy_session,
    get_session_id,
)

router = APIRouter()


class CreateSessionRequest(BaseModel):
    conversation_id: int
    avatar: str | None = None


class SpeakRequest(BaseModel):
    conversation_id: int
    text: str


class InterruptRequest(BaseModel):
    conversation_id: int


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