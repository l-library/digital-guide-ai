import asyncio
import os
import uuid

import edge_tts

VOICE = os.getenv("TTS_VOICE", "zh-CN-YunxiNeural")
MAX_TEXT_LENGTH = 2000  # edge-tts 单次合成文本上限
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 秒
REQUEST_TIMEOUT = 30.0  # 秒


async def _synthesize_with_retry(text: str, voice: str, output_path: str) -> bool:
    """带重试的单次合成，应对 edge-tts 偶发网络故障"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await asyncio.wait_for(communicate.save(output_path), timeout=REQUEST_TIMEOUT)
            return True
        except asyncio.TimeoutError:
            last_error = f"超时（{REQUEST_TIMEOUT}s）"
        except Exception as e:
            last_error = str(e)

        if attempt < MAX_RETRIES - 1:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"[TTS] 第{attempt + 1}次重试，等待{delay:.1f}s... (原因: {last_error})")
            await asyncio.sleep(delay)

    print(f"[TTS] 合成最终失败（{MAX_RETRIES}次重试后）: {last_error}")
    return False


async def synthesize_audio(text: str, output_path: str) -> bool:
    """将文字合成语音并保存到本地，支持自动重试"""
    if not text or not text.strip():
        print("[TTS] 输入文本为空，跳过合成")
        return False

    if len(text) > MAX_TEXT_LENGTH:
        print(f"[TTS] 文本过长（{len(text)}字），截断至{MAX_TEXT_LENGTH}字")
        text = text[:MAX_TEXT_LENGTH]

    return await _synthesize_with_retry(text, VOICE, output_path)


async def synthesize_to_file(text: str, output_dir: str) -> str | None:
    """合成语音并保存到指定目录，返回文件名；失败返回None"""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"tts_{uuid.uuid4().hex[:12]}.mp3"
    output_path = os.path.join(output_dir, filename)
    success = await synthesize_audio(text, output_path)
    if success:
        return filename
    return None
