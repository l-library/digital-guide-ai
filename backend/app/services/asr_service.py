import whisper
import torch
import warnings
import os
warnings.filterwarnings("ignore")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"ASR 语音模块初始化中... 使用: {device}")

print("正在加载 Whisper Medium 模型，这可能需要一点时间...")
# 如果之前没下载过，运行这行代码时后台会开始下载约 1.5GB 的模型权重
model = whisper.load_model("medium", device=device) # 我用的是medium，如果设备带不动可以换成更小的tiny或base

# 获取 backend/models 的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(current_dir, "..", "..", "models")

# 让Whisper去指定的 models 文件夹里找
model = whisper.load_model("medium", device=device, download_root=models_dir)
def transcribe_audio(audio_path: str) -> str:
    """
    将音频文件转为文本（含语境增强）
    """
    try:
        # 给模型注入语境（让它能识别一些专有名词，这个后面可以改得更详细一些）
        prompt_text = "这是一段关于无锡灵山景点的旅游咨询对话。关键词包含：灵山胜境、灵山、门票、历史由来、九龙灌浴、梵宫等。"
        
        # 加上 language 和 initial_prompt 参数
        result = model.transcribe(
            audio_path,
            language="zh",               # 强制约束为中文
            initial_prompt=prompt_text   # 提前告诉它接下来会听到什么领域的词
        )
        return result["text"]
    except Exception as e:
        return f"语音识别失败: {str(e)}"