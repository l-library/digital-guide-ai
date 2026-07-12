"""
CosyVoice TTS 线程安全封装。

使用 CosyVoice 的 AutoModel 进行语音合成，通过 asyncio.Semaphore(2) 控制
GPU 推理并发数（最多 2 个并行推理，平衡吞吐量和显存占用）。
"""

import asyncio
import os
import sys
import logging

import torch

logger = logging.getLogger(__name__)
import torchaudio

COSYVOICE_DIR = os.getenv("COSYVOICE_DIR", "/home/liborui/CosyVoice")
MATCHA_TTS_DIR = os.getenv("COSYVOICE_MATCHA_DIR", os.path.join(COSYVOICE_DIR, "third_party/Matcha-TTS"))

_ALREADY_INJECTED = False


def _inject_paths():
    """向 sys.path 注入 CosyVoice / Matcha-TTS 路径，仅执行一次。"""
    global _ALREADY_INJECTED
    if _ALREADY_INJECTED:
        return
    sys.path.insert(0, COSYVOICE_DIR)
    sys.path.insert(0, MATCHA_TTS_DIR)
    _ALREADY_INJECTED = True


class CosyVoiceTTS:
    """CosyVoice 语音合成服务的线程安全封装。

    使用示例::

        tts = CosyVoiceTTS("/home/liborui/CosyVoice/pretrained_models/CosyVoice-300M-SFT")
        tts.load()
        success = await tts.synthesize_to_file("你好世界", "/tmp/out.wav")
    """

    def __init__(
        self,
        model_dir: str,
        device: str = "cuda",
        fp16: bool = True,
    ):
        """存储配置，不加载模型（模型在 load() 中延迟加载）。"""
        self._model_dir = model_dir
        self._device = device
        self._fp16 = fp16

        self._model = None
        self.sample_rate: int = 0

        self._lock = asyncio.Semaphore(2)

    def load(self) -> None:
        """加载 CosyVoice AutoModel。

        先注入 sys.path，再导入 AutoModel 并实例化。
        """
        _inject_paths()

        from cosyvoice.cli.cosyvoice import AutoModel

        self._model = AutoModel(model_dir=self._model_dir)
        self.sample_rate = self._model.sample_rate

        try:
            spks = self._model.list_available_spks()
            logger.info(f"可用音色: {spks}")
        except Exception:
            logger.warning("获取可用音色列表失败")

        logger.info("模型加载完成")

        # 预热推理：触发 CUDA kernel JIT 编译，避免首次用户请求延迟
        logger.info("正在预热推理...")
        try:
            self.synthesize("预热。", speaker="中文女")
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            logger.info("预热完成")
        except Exception as e:
            logger.warning(f"预热失败（不影响正常使用）: {e}")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def synthesize(
        self,
        text: str,
        speaker: str = "中文女",
    ) -> torch.Tensor | None:
        """同步语音合成，返回音频张量。

        Args:
            text: 待合成文本
            speaker: 说话人名称，默认 "中文女"

        Returns:
            torch.Tensor: 音频张量（单声道，采样率见 self.sample_rate）
            None: 输入为空或合成失败
        """
        if not text or not text.strip():
            return None

        if self._model is None:
            raise RuntimeError("模型尚未加载，请先调用 load()")

        # AutoModel.inference_sft 返回 generator，我们只取第一次结果
        for i, result in enumerate(self._model.inference_sft(
            text, speaker, stream=False
        )):
            return result["tts_speech"]

        return None

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speaker: str = "中文女",
    ) -> bool:
        """异步安全地将语音合成结果写入 WAV 文件。

        内部通过 asyncio.Semaphore(2) 控制最多 2 个 GPU 推理并行执行。

        Args:
            text: 待合成文本
            output_path: 输出 WAV 文件路径
            speaker: 说话人名称

        Returns:
            bool: 合成成功返回 True，失败（空文本/异常）返回 False
        """
        if not text or not text.strip():
            return False

        async with self._lock:
            try:
                audio = await asyncio.to_thread(
                    self.synthesize, text, speaker
                )
                if audio is None:
                    return False

                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                await asyncio.to_thread(
                    torchaudio.save, output_path, audio, self.sample_rate
                )
                return True
            except Exception as e:
                logger.error(f"合成失败: {e}")
                return False
            finally:
                # 释放碎片化 CUDA 内存，防止多句合成时 OOM
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
