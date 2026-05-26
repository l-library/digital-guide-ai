import asyncio
import json
import os
import re
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.rag_service import retrieve_context, build_prompt
from app.services.llm_service import generate_stream_async, generate_title_async
from app.services.tts_service import synthesize_to_file
from app.services.digital_human_client import get_client as get_dh_client
from app.services.digital_human_session import get_session_id
from app.models import Conversation, Message
from app.database import SessionLocal
from sqlalchemy import func

router = APIRouter()

TEMP_AUDIO_DIR = os.path.abspath(os.path.join("data", "temp_audios"))
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


async def _send_audio_to_livetalking(conversation_id: int, audio_filename: str):
    """将 TTS 生成的音频文件发送给 LiveTalking，驱动口型动画"""
    sessionid = get_session_id(conversation_id)
    if sessionid is None:
        return
    filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        await get_dh_client().send_audio(sessionid, audio_bytes)
    except Exception as e:
        print(f"[LiveTalking音频推送失败] conversation_id={conversation_id}: {e}")


def _split_sentences(text: str) -> list[str]:
    """按中文句号、感叹号、问号、换行符切分句子，过滤空串"""
    return [s for s in re.split(r'[。！？\n]+', text) if s.strip()]


# TTS Future 队列：合成并发执行，但播报按 LLM 生成顺序严格串行
_tts_queues: dict[int, asyncio.Queue] = {}


async def _tts_player(conversation_id: int, queue: asyncio.Queue):
    """顺序消费队列中的 TTS Future，逐句发送给 LiveTalking 播报"""
    try:
        while True:
            future = await queue.get()
            if future is None:
                break
            try:
                audio_filename = await future
                if not audio_filename:
                    continue
            except Exception as e:
                print(f"[TTS合成异常] conv={conversation_id}: {e}")
                continue
            try:
                await _send_audio_to_livetalking(conversation_id, audio_filename)
                filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
                file_size = os.path.getsize(filepath)
                duration = file_size / 5000 + 0.3
                await asyncio.sleep(duration)
            except Exception as e:
                print(f"[TTS播报失败] conv={conversation_id}: {e}")
    finally:
        _tts_queues.pop(conversation_id, None)


async def _synthesize_and_resolve(text: str, future: asyncio.Future):
    try:
        audio_filename = await synthesize_to_file(text, TEMP_AUDIO_DIR)
        future.set_result(audio_filename if audio_filename else None)
    except Exception as e:
        print(f"[逐句TTS合成失败]: {e}")
        future.set_result(None)


def _enqueue_tts_sync(text: str, queue: asyncio.Queue) -> asyncio.Future:
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    queue.put_nowait(future)
    return future


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
                sentence_buffer = ""
                queue = asyncio.Queue()
                _tts_queues[conversation_id] = queue
                player_task = asyncio.create_task(_tts_player(conversation_id, queue))
                try:
                    async for token in generate_stream_async(messages_for_llm):
                        full_content += token
                        sentence_buffer += token
                        if sentence_buffer and sentence_buffer[-1] in "。！？\n":
                            sentences = _split_sentences(sentence_buffer)
                            for s in sentences:
                                await send_json(
                                    {
                                        "type": "sentence",
                                        "conversation_id": conversation_id,
                                        "content": s,
                                    }
                                )
                                if response_type == 1:
                                    future = _enqueue_tts_sync(s, queue)
                                    asyncio.create_task(_synthesize_and_resolve(s, future))
                            sentence_buffer = ""
                        await send_json(
                            {
                                "type": "token",
                                "conversation_id": conversation_id,
                                "content": token,
                            }
                        )
                    if sentence_buffer.strip():
                        remaining = sentence_buffer.strip()
                        await send_json(
                            {
                                "type": "sentence",
                                "conversation_id": conversation_id,
                                "content": remaining,
                            }
                        )
                        if response_type == 1:
                            future = _enqueue_tts_sync(remaining, queue)
                            asyncio.create_task(_synthesize_and_resolve(remaining, future))
                    if response_type == 1:
                        await queue.put(None)
                except Exception as gen_err:
                    if response_type == 1:
                        await queue.put(None)
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

                audio_url = None
                if response_type == 1:
                    try:
                        audio_filename = await synthesize_to_file(
                            full_content, TEMP_AUDIO_DIR
                        )
                        if audio_filename:
                            audio_url = (
                                f"/api/v1/download_audio?filename={audio_filename}"
                            )
                    except Exception as e:
                        print(f"[TTS失败] {e}")

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
