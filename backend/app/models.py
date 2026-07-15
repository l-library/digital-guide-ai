"""
数据库模型：对话（Conversation）和消息（Message）
"""
import json
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, Float, Integer, String, Text, DateTime, ForeignKey, JSON, func
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
    knowledge_sources = Column(JSON, nullable=True)  # JSON数组，如 ["灵山胜境导游词.docx"]
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

class KnowledgeDoc(Base):
    """知识文档表"""
    __tablename__ = "knowledge_docs"

    # 对应 API 里的 doc_id
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 业务字段
    title = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)       # 例如docx, pdf
    file_size = Column(Integer, nullable=False, default=0) # 文件大小(字节)
    
    file_path = Column(String(512), nullable=False)      
    
    # 状态与统计 (uploaded, processing, ready, failed)
    status = Column(String(32), nullable=False, default="uploaded")
    chunk_count = Column(Integer, nullable=False, default=0)
    content_preview = Column(Text, nullable=True)        # 提取后的一小段文本预览
    
    # 关联信息
    user_id = Column(Integer, nullable=False, index=True) # 哪个管理员上传的
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """将模型对象转换为 API 规范要求的 JSON 字典格式"""
        return {
            "doc_id": self.id,  # 这里数据库叫 id，API 叫 doc_id
            "title": self.title,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "content_preview": self.content_preview,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    display_name = Column(String(50), nullable=False)
    role = Column(String(16), nullable=False, default="visitor")
    is_active = Column(Boolean, default=True)
    token_version = Column(Integer, default=0)
    phone = Column(String(20), nullable=True)
    email = Column(String(128), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    interests = Column(String(512), nullable=True, default="[]")
    last_interest_update = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    def to_dict(self):
        """用户信息字典（不含密码哈希）"""
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "phone": self.phone,
            "email": self.email,
            "is_active": self.is_active,
            "avatar_url": self.avatar_url,
            "interests": json.loads(self.interests) if self.interests else [],
            "last_interest_update": self.last_interest_update.isoformat() + "Z" if self.last_interest_update else None,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }


class RecommendLog(Base):
    """推荐日志表"""
    __tablename__ = "recommend_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    interests_used = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VisitorConsumption(Base):
    """游客消费记录表（用于管理端消费分析/营销决策展示）

    数据来源：backend/data/data.csv（灵山胜境游客消费模拟数据）。
    设计参考 api.md 第二章的响应信封规范，to_dict() 输出可直接作为 `data` 字段。
    """
    __tablename__ = "visitor_consumption"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tourist_id = Column(String(16), nullable=False, index=True)           # 例: U00055
    user_nickname = Column(String(64), nullable=True)                    # 游客昵称
    age = Column(Integer, nullable=True)                                 # 年龄
    gender = Column(String(4), nullable=True)                            # 男/女
    attraction_name = Column(String(64), nullable=True)                   # 景点名称
    attraction_type = Column(String(64), nullable=True)                   # 景点类型
    visit_date = Column(Date, nullable=False, index=True)                 # 到访日期
    stay_duration = Column(Float, nullable=True)                          # 停留时长（小时）
    ticket_cost = Column(Float, nullable=False, default=0)                # 门票消费
    food_cost = Column(Float, nullable=False, default=0)                  # 餐饮消费
    shopping_cost = Column(Float, nullable=False, default=0)              # 购物消费
    transport_cost = Column(Float, nullable=False, default=0)             # 交通消费
    entertainment_cost = Column(Float, nullable=False, default=0)         # 娱乐消费
    total_cost = Column(Float, nullable=False, default=0)                 # 总消费
    group_size = Column(Integer, nullable=True)                           # 同行人数
    satisfaction = Column(Integer, nullable=True)                        # 满意度 1-5
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tourist_id": self.tourist_id,
            "user_nickname": self.user_nickname,
            "age": self.age,
            "gender": self.gender,
            "attraction_name": self.attraction_name,
            "attraction_type": self.attraction_type,
            "visit_date": self.visit_date.isoformat() if self.visit_date else None,
            "stay_duration": self.stay_duration,
            "ticket_cost": self.ticket_cost,
            "food_cost": self.food_cost,
            "shopping_cost": self.shopping_cost,
            "transport_cost": self.transport_cost,
            "entertainment_cost": self.entertainment_cost,
            "total_cost": self.total_cost,
            "group_size": self.group_size,
            "satisfaction": self.satisfaction,
        }