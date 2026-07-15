from fastapi import APIRouter
from .endpoints import auth, chat, conversations, digital_human, admin, dashboard, reports_api, recommend, consumption
from .endpoints.digital_human import (
    play_audio as digital_human_play_audio,
    play_audio_queue as digital_human_play_audio_queue,
    flush_audio_queue as digital_human_flush_audio_queue,
    PlayAudioRequest,
    FlushRequest,
)

api_router = APIRouter()
api_router.include_router(chat.router, tags=["游客交互"])
api_router.include_router(conversations.router, tags=["对话管理"])
api_router.include_router(digital_human.router, prefix="/digital-human", tags=["数字人"])
api_router.include_router(auth.router, tags=["认证"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理员操作"])
api_router.include_router(dashboard.router, prefix="/admin/dashboard", tags=["数据大屏"])
api_router.include_router(reports_api.router, prefix="/admin/reports", tags=["游客报告"])
api_router.include_router(recommend.router, prefix="/recommend", tags=["推荐"])
api_router.include_router(consumption.router, prefix="/admin/consumption", tags=["消费分析"])

# play-audio 暴露为顶层路径（不经过 /digital-human 前缀），前端直接调用
@api_router.post("/play-audio")
async def play_audio_route(req: PlayAudioRequest):
    return await digital_human_play_audio(req)


@api_router.post("/play-audio-queue")
async def play_audio_queue_route(req: PlayAudioRequest):
    return await digital_human_play_audio_queue(req)


@api_router.post("/flush")
async def flush_audio_queue_route(req: FlushRequest):
    return await digital_human_flush_audio_queue(req)
