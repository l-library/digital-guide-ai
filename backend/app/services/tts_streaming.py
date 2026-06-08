"""TTS 流式播报共享模块：逐句合成 + 严格串行播报

chat.py / websocket.py 共用的 TTS 流式播报基础设施。
设计：TTS 合成并发执行，播报按 LLM 输出顺序严格串行。
"""

import asyncio
import json
import os
import re
import subprocess
import uuid

from app.services.tts_service import synthesize_to_file
from app.services.digital_human_client import get_client as get_dh_client
from app.services.digital_human_session import get_session_id

TEMP_AUDIO_DIR = os.path.abspath(os.path.join("data", "temp_audios"))
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# TTS Future 队列：合成并发执行，但播报按 LLM 生成顺序严格串行
# key 为 stream_id（每请求唯一 uuid），避免同一 conversation 并发冲突
_tts_queues: dict[str, asyncio.Queue] = {}


def split_sentences(text: str) -> list[str]:
    """按中文句号/感叹号/问号/换行拆分句子，过滤空串"""
    return [s for s in re.split(r'[。！？\n]+', text) if s.strip()]


def get_wav_duration(filepath: str) -> float:
    """读取 WAV 文件的实际播放时长（秒）。"""
    # 优先：ffprobe
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", filepath],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
            if duration > 0:
                return duration
    except Exception as e:
        print(f"[TTS] ffprobe 获取时长失败: {e}")

    # 回退：soundfile WAV header
    try:
        import soundfile as sf
        return sf.info(filepath).duration
    except Exception as e:
        print(f"[TTS] soundfile 获取时长失败: {e}")

    # 最终回退：根据文件大小估算（16-bit mono 22050Hz ≈ 44100 bytes/s）
    return os.path.getsize(filepath) / 44100.0


async def send_audio_to_livetalking(conversation_id: int, audio_filename: str):
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


async def _tts_player(stream_id: str, conversation_id: int, queue: asyncio.Queue):
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
                print(f"[TTS合成异常] stream={stream_id}: {e}")
                continue
            try:
                await send_audio_to_livetalking(conversation_id, audio_filename)
                filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
                duration = get_wav_duration(filepath) + 0.1
                await asyncio.sleep(duration)
            except Exception as e:
                print(f"[TTS播报失败] stream={stream_id}: {e}")
    finally:
        _tts_queues.pop(stream_id, None)


async def synthesize_and_resolve(text: str, future: asyncio.Future):
    """合成 TTS 并将结果设置到 future；future 已在主协程中同步入队"""
    try:
        audio_filename = await synthesize_to_file(text, TEMP_AUDIO_DIR)
        future.set_result(audio_filename if audio_filename else None)
    except Exception as e:
        print(f"[逐句TTS合成失败]: {e}")
        future.set_result(None)


def enqueue_tts_sync(text: str, queue: asyncio.Queue) -> asyncio.Future:
    """在主协程中同步将 TTS future 入队，消除竞态条件"""
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    queue.put_nowait(future)
    return future


def create_tts_queue(conversation_id: int) -> tuple[str, asyncio.Queue, asyncio.Task]:
    """创建一个新的 TTS 流式播报队列

    Returns:
        (stream_id, queue, player_task) — stream_id 用于后续清理，
        player_task 已在后台运行等待消费。
    """
    stream_id = uuid.uuid4().hex[:12]
    queue: asyncio.Queue = asyncio.Queue()
    _tts_queues[stream_id] = queue
    player_task = asyncio.create_task(
        _tts_player(stream_id, conversation_id, queue)
    )
    return stream_id, queue, player_task
