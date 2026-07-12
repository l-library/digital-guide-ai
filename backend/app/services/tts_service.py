import asyncio
import os
import time
import uuid
import logging
logger = logging.getLogger(__name__)

from app.services.cosyvoice_tts import CosyVoiceTTS

TTS_SPEAKER = os.getenv("TTS_SPEAKER", "中文女")
MAX_TEXT_LENGTH = 1000
REQUEST_TIMEOUT = 60.0

_tts_instance: CosyVoiceTTS | None = None


def init_tts_model(model_dir: str):
    """初始化 TTS 模型（供 lifespan 调用）。"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = CosyVoiceTTS(model_dir=model_dir)
        _tts_instance.load()
    return _tts_instance


async def synthesize_audio(text: str, output_path: str) -> bool:
    """将文字合成语音并保存到本地。"""
    if _tts_instance is None:
        logger.error("[TTS] 模型尚未初始化，请先调用 init_tts_model()")
        return False

    if not text or not text.strip():
        logger.error("[TTS] 输入文本为空，跳过合成")
        return False

    if len(text) > MAX_TEXT_LENGTH:
        logger.error(f"[TTS] 文本过长（{len(text)}字），截断至{MAX_TEXT_LENGTH}字")
        text = text[:MAX_TEXT_LENGTH]

    try:
        return await asyncio.wait_for(
            _tts_instance.synthesize_to_file(text, output_path, speaker=TTS_SPEAKER),
            timeout=REQUEST_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(f"[TTS] 合成超时（{REQUEST_TIMEOUT}s）")
        return False
    except Exception as e:
        logger.error(f"[TTS] 合成失败: {e}")
        return False


async def synthesize_to_file(text: str, output_dir: str) -> str | None:
    """合成语音并保存到指定目录，返回文件名；失败返回None。"""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"tts_{uuid.uuid4().hex[:12]}.wav"
    output_path = os.path.join(output_dir, filename)
    success = await synthesize_audio(text, output_path)
    if success:
        return filename
    return None


def cleanup_old_audio(directory: str, max_age_hours: int = 1) -> int:
    """删除超过指定时长的 WAV 音频文件。

    Args:
        directory: 临时音频目录路径
        max_age_hours: 最大存活时长（小时）

    Returns:
        删除的文件数量
    """
    if not os.path.isdir(directory):
        logger.info(f"[清理] 目录不存在: {directory}")
        return 0

    now = time.time()
    max_age_seconds = max_age_hours * 3600
    deleted = 0

    for filename in os.listdir(directory):
        if not filename.lower().endswith(".wav"):
            continue

        filepath = os.path.join(directory, filename)
        try:
            file_age = now - os.path.getmtime(filepath)
            if file_age > max_age_seconds:
                os.remove(filepath)
                deleted += 1
        except (PermissionError, FileNotFoundError):
            continue

    if deleted > 0:
        logger.info(f"[清理] 已删除 {deleted} 个过期音频文件")
    return deleted
