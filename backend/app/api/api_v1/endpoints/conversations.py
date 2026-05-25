from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database import get_db
from app.models import Conversation, Message

router = APIRouter()


def ok(data):
    return {"code": 200, "message": "success", "data": data}


def fail(code: int, message: str):
    return {"code": code, "message": message, "data": {}}


def make_envelope(code: int, message: str, data=None):
    return {"code": code, "message": message, "data": data if data is not None else {}}


class CreateConversationRequest(BaseModel):
    user_id: int
    title: str = "新对话"
    knowledge_doc_id: int = -1


class UpdateConversationTitleRequest(BaseModel):
    title: str


@router.post("/conversations")
def create_conversation(req: CreateConversationRequest, db: Session = Depends(get_db)):
    conv = Conversation(
        user_id=req.user_id,
        title=req.title,
        knowledge_doc_id=req.knowledge_doc_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ok({
        "conversation_id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() + "Z" if conv.created_at else None,
    })


@router.get("/conversations")
def list_conversations(
    user_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(Conversation.id)).filter(Conversation.user_id == user_id).scalar()
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for c in convs:
        msg_count = db.query(func.count(Message.id)).filter(Message.conversation_id == c.id).scalar()
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == c.id)
            .order_by(desc(Message.created_at))
            .first()
        )
        items.append({
            "conversation_id": c.id,
            "title": c.title,
            "message_count": msg_count,
            "last_message": last_msg.content[:50] if last_msg else "",
            "last_time": last_msg.created_at.isoformat() + "Z" if last_msg and last_msg.created_at else None,
            "created_at": c.created_at.isoformat() + "Z" if c.created_at else None,
        })
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/conversations/grouped")
def list_conversations_grouped(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .all()
    )
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    today_list = []
    yesterday_list = []
    earlier_list = []

    for c in convs:
        msg_count = db.query(func.count(Message.id)).filter(Message.conversation_id == c.id).scalar()
        item = {
            "conversation_id": c.id,
            "title": c.title,
            "message_count": msg_count,
            "created_at": c.created_at.isoformat() + "Z" if c.created_at else None,
            "updated_at": c.updated_at.isoformat() + "Z" if c.updated_at else None,
        }
        if c.updated_at and c.updated_at >= today_start:
            today_list.append(item)
        elif c.updated_at and c.updated_at >= yesterday_start:
            yesterday_list.append(item)
        else:
            earlier_list.append(item)

    groups = []
    if today_list:
        groups.append({"date": "今天", "conversations": today_list})
    if yesterday_list:
        groups.append({"date": "昨天", "conversations": yesterday_list})
    if earlier_list:
        groups.append({"date": "更早", "conversations": earlier_list})

    return ok({"groups": groups})


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return fail(404, "对话不存在")
    return ok(conv.to_dict())


@router.put("/conversations/{conversation_id}")
def update_conversation_title(
    conversation_id: int,
    req: UpdateConversationTitleRequest,
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return fail(404, "对话不存在")
    conv.title = req.title
    conv.updated_at = datetime.utcnow()
    db.commit()
    return ok({"conversation_id": conv.id, "title": conv.title, "updated_at": conv.updated_at.isoformat() + "Z"})


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return fail(404, "对话不存在")
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conv)
    db.commit()
    return ok({})


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return fail(404, "对话不存在")

    total = db.query(func.count(Message.id)).filter(Message.conversation_id == conversation_id).scalar()
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [m.to_dict() for m in msgs]
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/conversations/{conversation_id}/messages/all")
def get_all_messages(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return fail(404, "对话不存在")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    items = [m.to_dict() for m in msgs]
    return ok({"items": items, "total": len(items)})
