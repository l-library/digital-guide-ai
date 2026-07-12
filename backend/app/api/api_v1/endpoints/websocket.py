import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.rag_service import retrieve_context
from app.services.llm_service import generate_title_async
from app.services.streaming_utils import build_llm_messages
from app.services.tts_streaming import (
    create_streaming_pipeline,
)
from app.models import Conversation, Message
from app.database import SessionLocal
from sqlalchemy import func

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()

    async def send_json(msg: dict):
        await ws.send_text(json.dumps(msg, ensure_ascii=False))

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await send_json({"type": "pong"})
                continue

            if msg_type != "chat_message":
                await send_json({"type": "error", "message": "未知消息类型"})
                continue

            conversation_id = data.get("conversation_id", 0)
            content = data.get("content", "")
            response_type = data.get("response_type", 0)

            if not content.strip():
                await send_json(
                    {
                        "type": "error",
                        "conversation_id": conversation_id,
                        "message": "消息内容不能为空",
                    }
                )
                continue

            db = SessionLocal()
            try:
                conv = (
                    db.query(Conversation)
                    .filter(Conversation.id == conversation_id)
                    .first()
                )
                if not conv:
                    await send_json(
                        {
                            "type": "error",
                            "conversation_id": conversation_id,
                            "message": "对话不存在",
                        }
                    )
                    db.close()
                    continue

                user_msg = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=content,
                )
                db.add(user_msg)
                db.commit()

                history_msgs = (
                    db.query(Message)
                    .filter(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                    .all()
                )

                context_list = retrieve_context(content)
                messages_for_llm = build_llm_messages(
                    history_msgs, content, context_list
                )

                try:
                    async for event in create_streaming_pipeline(
                        conversation_id, response_type, messages_for_llm
                    ):
                        if event["type"] == "_pipeline_done":
                            full_content = event["full_content"]
                            break
                        await send_json(event)
                except Exception:
                    db.rollback()
                    db.close()
                    continue

                audio_url = None

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                    audio_url=audio_url,
                )
                db.add(assistant_msg)
                conv.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(assistant_msg)

                knowledge_sources = []
                if context_list:
                    knowledge_sources = ["景区知识库"]

                await send_json(
                    {
                        "type": "done",
                        "conversation_id": conversation_id,
                        "message_id": assistant_msg.id,
                        "full_content": full_content,
                        "audio_url": audio_url,
                        "knowledge_sources": knowledge_sources,
                    }
                )

                # 第一轮对话结束后自动生成标题
                msg_count = (
                    db.query(func.count(Message.id))
                    .filter(Message.conversation_id == conversation_id)
                    .scalar()
                )
                if msg_count <= 2:
                    try:
                        title = await generate_title_async(content, full_content)
                        conv.title = title
                        db.commit()
                        await send_json(
                            {
                                "type": "title_updated",
                                "conversation_id": conversation_id,
                                "title": title,
                            }
                        )
                    except Exception as e:
                        logger.error(f"[标题生成失败] conversation_id={conversation_id}: {e}")

            except Exception as e:
                db.rollback()
                await send_json(
                    {
                        "type": "error",
                        "conversation_id": conversation_id,
                        "message": f"服务器错误: {str(e)}",
                    }
                )
            finally:
                db.close()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await send_json({"type": "error", "message": f"连接异常: {str(e)}"})
        except Exception:
            pass
