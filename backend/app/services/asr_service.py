import logging

import whisper
import torch
import warnings
import os
from app.config.paths import MODELS_DIR

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")

_device = "cpu"
logger.info(f"语音模块将使用设备: {_device}")

_model = None


def _get_model():
    """懒加载 Whisper 模型，避免模块导入时阻塞"""
    global _model
    if _model is None:
        logger.info("正在加载 Whisper Base 模型，首次加载可能需要较长时间...")
        _model = whisper.load_model("base", device=_device, download_root=MODELS_DIR)
        logger.info("Whisper 模型加载完成")
    return _model


def transcribe_audio(audio_path: str) -> str:
    """
    将音频文件转为文本
    """
    import subprocess

    try:
        abs_path = os.path.abspath(audio_path)
        if not os.path.exists(abs_path):
            return f"语音识别失败: 音频文件不存在: {abs_path}"

        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)

        model = _get_model()
        result = model.transcribe(abs_path, language="zh")
        return result["text"].strip()
    except FileNotFoundError:
        return "语音识别失败: 未找到 ffmpeg，请安装 ffmpeg 并将其添加到系统 PATH"
    except subprocess.CalledProcessError:
        return "语音识别失败: ffmpeg 不可用，请检查 ffmpeg 安装"
    except Exception as e:
        return f"语音识别失败: {str(e)}"
