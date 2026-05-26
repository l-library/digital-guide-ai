from fastapi import APIRouter
from .endpoints import chat, conversations, digital_human
from app.api.api_v1.endpoints import chat, conversations, admin
from .endpoints import chat, conversations

api_router = APIRouter()
api_router.include_router(chat.router, tags=["游客交互"])
api_router.include_router(conversations.router, tags=["对话管理"])
api_router.include_router(digital_human.router, prefix="/digital-human", tags=["数字人"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理员操作"])
