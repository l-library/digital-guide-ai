import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.rag_service import retrieve_context, build_prompt
from app.services.llm_service import generate_stream
from app.models import Conversation, Message
from app.database import SessionLocal

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

            if not content.strip():
                await send_json({"type": "error", "conversation_id": conversation_id, "message": "消息内容不能为空"})
                continue

            db = SessionLocal()
            try:
                conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
                if not conv:
                    await send_json({"type": "error", "conversation_id": conversation_id, "message": "对话不存在"})
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

                messages_for_llm = []
                for m in history_msgs:
                    messages_for_llm.append({"role": m.role, "content": m.content})

                context_list = retrieve_context(content)
                prompt_text = build_prompt(content, context_list)

                if len(messages_for_llm) <= 2:
                    messages_for_llm = [{"role": "user", "content": prompt_text}]
                else:
                    system_msg = {
                        "role": "system",
                        "content": (
                            "你是灵山胜境景区的AI导游。回答简洁，150字内。"
                            "语气自然亲切。不要使用emoji或动作描写。"
                            "如果资料中没有相关信息，请如实告知。"
                        ),
                    }
                    context_msg = {
                        "role": "system",
                        "content": f"参考景区资料：\n{chr(10).join(context_list)}",
                    }
                    history_without_last = messages_for_llm[:-1]
                    last_user_msg = messages_for_llm[-1]
                    messages_for_llm = [system_msg, context_msg] + history_without_last + [last_user_msg]

                full_content = ""
                try:
                    for token in generate_stream(messages_for_llm):
                        full_content += token
                        await send_json({
                            "type": "token",
                            "conversation_id": conversation_id,
                            "content": token,
                        })
                except Exception as gen_err:
                    await send_json({
                        "type": "error",
                        "conversation_id": conversation_id,
                        "message": f"LLM生成失败: {str(gen_err)}",
                    })
                    db.rollback()
                    db.close()
                    continue

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                )
                db.add(assistant_msg)
                db.commit()
                db.refresh(assistant_msg)

                knowledge_sources = []
                if context_list:
                    knowledge_sources = ["景区知识库"]

                await send_json({
                    "type": "done",
                    "conversation_id": conversation_id,
                    "message_id": assistant_msg.id,
                    "full_content": full_content,
                    "audio_url": None,
                    "knowledge_sources": knowledge_sources,
                })

            except Exception as e:
                db.rollback()
                await send_json({
                    "type": "error",
                    "conversation_id": conversation_id,
                    "message": f"服务器错误: {str(e)}",
                })
            finally:
                db.close()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await send_json({"type": "error", "message": f"连接异常: {str(e)}"})
        except Exception:
            pass
