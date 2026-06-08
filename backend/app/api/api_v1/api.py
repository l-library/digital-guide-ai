from fastapi import APIRouter
from .endpoints import chat, conversations, digital_human, admin
from .endpoints.digital_human import play_audio as digital_human_play_audio, PlayAudioRequest

api_router = APIRouter()
api_router.include_router(chat.router, tags=["游客交互"])
api_router.include_router(conversations.router, tags=["对话管理"])
api_router.include_router(digital_human.router, prefix="/digital-human", tags=["数字人"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理员操作"])

# play-audio 暴露为顶层路径（不经过 /digital-human 前缀），前端直接调用
@api_router.post("/play-audio")
async def play_audio_route(req: PlayAudioRequest):
    return await digital_human_play_audio(req)
