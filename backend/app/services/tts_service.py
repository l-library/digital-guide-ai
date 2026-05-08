import edge_tts

# 一个中文女声
VOICE = "zh-CN-XiaoxiaoNeural"

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