import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.rag_service import retrieve_context, build_prompt
from app.services.llm_service import generate_stream_async, generate_title_async
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
                            "你是一名经验丰富的景区导游。作为一名导游，你需要为用户提供丰富、有趣的旅行体验。"
                            "核心技能：丰富的旅游知识储备、出色的沟通和表达能力、创意思维和创新能力"
                            "你的工作准则是提供准确、可靠的旅游信息、尊重不同文化和地区的习俗、以用户为中心，满足个性化需求"
                            "工作流程：了解用户需求和偏好、引导用户说出自己的需求、提供详细解说和互动、收集用户反馈，持续优化体验"
                            "沟通风格：保持热情、友好、幽默的态度，让用户感受到愉快的虚拟旅游体验。"
                            "价值观：尊重文化多样性、提供真实、有价值的旅游信息、注重用户体验，满足个性化需求"
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
                    messages_for_llm = (
                        [system_msg, context_msg]
                        + history_without_last
                        + [last_user_msg]
                    )

                full_content = ""
                try:
                    async for token in generate_stream_async(messages_for_llm):
                        full_content += token
                        await send_json(
                            {
                                "type": "token",
                                "conversation_id": conversation_id,
                                "content": token,
                            }
                        )
                except Exception as gen_err:
                    await send_json(
                        {
                            "type": "error",
                            "conversation_id": conversation_id,
                            "message": f"LLM生成失败: {str(gen_err)}",
                        }
                    )
                    db.rollback()
                    db.close()
                    continue

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
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
                        "audio_url": None,
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
                        print(f"[标题生成失败] conversation_id={conversation_id}: {e}")

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
