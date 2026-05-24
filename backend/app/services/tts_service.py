import edge_tts
import os
import uuid

VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")


async def synthesize_audio(text: str, output_path: str):
    """
    将文字合成语音并保存到本地
    """
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"语音合成失败: {str(e)}")
        return False


async def synthesize_to_file(text: str, output_dir: str) -> str | None:
    """
    合成语音并保存到指定目录，返回文件名；失败返回None
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"tts_{uuid.uuid4().hex[:12]}.mp3"
    output_path = os.path.join(output_dir, filename)
    success = await synthesize_audio(text, output_path)
    if success:
        return filename
    return None
