"""
数据库模型：对话（Conversation）和消息（Message）
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from app.database import Base


class Conversation(Base):
    """对话表"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(128), nullable=False, default="新对话")
    knowledge_doc_id = Column(Integer, nullable=True, default=-1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "knowledge_doc_id": self.knowledge_doc_id,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class Message(Base):
    """消息表"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # "user" 或 "assistant"
    content = Column(Text, nullable=False)
    audio_url = Column(String(512), nullable=True)
    knowledge_sources = Column(JSON, nullable=True)  # JSON数组，如 ["故宫介绍.docx"]
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "audio_url": self.audio_url,
            "knowledge_sources": self.knowledge_sources,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }

