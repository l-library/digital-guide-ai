"""数字人会话映射管理器：将 FastAPI conversation_id 映射到 LiveTalking sessionid。"""

import logging

import httpx

from app.services.digital_human_client import get_client

logger = logging.getLogger(__name__)

# conversation_id → LiveTalking sessionid
_sessions: dict[int, str] = {}


async def create_digital_human_session(conversation_id: int) -> str:
    """为 conversation_id 创建或复用 LiveTalking 会话，返回 sessionid。"""
    existing = _sessions.get(conversation_id)
    if existing is not None:
        logger.info("conversation_id=%d 已有映射 sessionid=%s，直接复用", conversation_id, existing)
        return existing

    try:
        data = await get_client().create_session()
    except httpx.HTTPError as exc:
        logger.warning("创建 LiveTalking 会话失败 (conversation_id=%d): %s", conversation_id, exc)
        raise

    sessionid = data.get("sessionid")
    if not sessionid:
        raise RuntimeError(f"LiveTalking create_session 返回数据缺少 sessionid: {data}")

    _sessions[conversation_id] = sessionid
    logger.info("conversation_id=%d 映射到 sessionid=%s", conversation_id, sessionid)
    return sessionid


def get_session_id(conversation_id: int) -> str | None:
    """查询 conversation_id 对应的 LiveTalking sessionid，无映射时返回 None。"""
    return _sessions.get(conversation_id)


async def destroy_session(conversation_id: int) -> bool:
    """销毁 conversation_id 对应的 LiveTalking 会话并移除映射。成功返回 True，无映射返回 False。"""
    sessionid = _sessions.pop(conversation_id, None)
    if sessionid is None:
        logger.warning("conversation_id=%d 无映射，无法销毁", conversation_id)
        return False

    try:
        await get_client().destroy_session(sessionid)
    except httpx.HTTPError as exc:
        logger.warning("销毁 LiveTalking 会话失败 (sessionid=%s): %s", sessionid, exc)
        # 映射已移除，仍返回 True 表示本地清理完成
    return True