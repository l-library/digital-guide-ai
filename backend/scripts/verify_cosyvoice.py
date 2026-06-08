#!/usr/bin/env python3
"""
CosyVoice 模型验证脚本
加载 CosyVoice-300M-SFT 模型，执行合成测试，验证输出。
用法:
    python backend/scripts/verify_cosyvoice.py --model_dir /path/to/CosyVoice-300M-SFT --text "你好测试" --output /tmp/test.wav
"""

import argparse
import os
import subprocess
import sys
import time

# CosyVoice 和 Matcha-TTS 依赖路径
sys.path.insert(0, os.getenv('COSYVOICE_DIR', '/home/liborui/CosyVoice'))
sys.path.insert(0, os.getenv('COSYVOICE_MATCHA_DIR', '/home/liborui/CosyVoice/third_party/Matcha-TTS'))

import torch
import torchaudio
from cosyvoice.cli.cosyvoice import AutoModel


def get_vram_usage(label=""):
    """通过 nvidia-smi 查询当前显存使用量 (MiB)。"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader'],
            capture_output=True, text=True, check=True
        )
        vram = result.stdout.strip()
        print(f"[VRAM {label}] {vram} MiB")
        return vram
    except Exception as e:
        print(f"[VRAM {label}] 无法获取: {e}")
        return "N/A"


def main():
    parser = argparse.ArgumentParser(description="CosyVoice 模型验证脚本")
    parser.add_argument('--model_dir', required=True, help='模型目录路径')
    parser.add_argument('--text', default='你好测试，欢迎使用语音合成系统。', help='合成文本')
    parser.add_argument('--output', default='/tmp/test.wav', help='输出音频路径')
    args = parser.parse_args()

    print(f"PyTorch 版本: {torch.__version__}")
    print(f"CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA 设备: {torch.cuda.get_device_name(0)}")

    # 加载前显存
    get_vram_usage("加载前")

    print(f"\n加载模型: {args.model_dir}")
    t0 = time.time()
    model = AutoModel(model_dir=args.model_dir)
    t1 = time.time()
    print(f"模型加载耗时: {t1 - t0:.2f}s")

    # 加载后显存
    get_vram_usage("加载后")

    # 显示可用说话人
    spks = model.list_available_spks()
    print(f"\n可用说话人 ({len(spks)}):")
    for spk in spks:
        print(f"  - {spk}")

    if '中文女' not in spks:
        print("警告: '中文女' 不在可用说话人列表中，将使用第一个说话人")
        target_spk = spks[0]
    else:
        target_spk = '中文女'

    print(f"\n合成文本: \"{args.text}\"")
    print(f"使用说话人: {target_spk}")
    print(f"采样率: {model.sample_rate}")

    # 合成
    t0 = time.time()
    for i, result in enumerate(model.inference_sft(args.text, target_spk, stream=False)):
        audio = result['tts_speech']  # torch.Tensor, shape: (T,)
        print(f"生成结果 {i}: shape={audio.shape}, dtype={audio.dtype}")
        break
    t1 = time.time()
    print(f"合成耗时: {t1 - t0:.2f}s")

    # 保存
    # audio shape 已经是 (1, T), 直接保存
    torchaudio.save(args.output, audio, model.sample_rate)
    print(f"\n音频已保存: {args.output}")
    print(f"  采样率: {model.sample_rate} Hz")
    print(f"  时长: {audio.shape[1] / model.sample_rate:.2f}s")
    print(f"  形状: {audio.shape}")

    # 合成后显存
    get_vram_usage("合成后")

    print("\n验证完成!")


if __name__ == '__main__':
    main()
