from fastapi import APIRouter
from .endpoints import chat, conversations

api_router = APIRouter()
api_router.include_router(chat.router, tags=["游客交互"])
api_router.include_router(conversations.router, tags=["对话管理"])