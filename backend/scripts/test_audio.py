import asyncio
import sys
import os
import time

# 将 backend 根目录加入 sys.path，以便能找到 app 模块
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.asr_service import transcribe_audio
from app.services.tts_service import init_tts_model, synthesize_audio

async def main():
    print("\n" + "="*50)
    print("语音测试")
    print("="*50)

    # 初始化 TTS 模型
    model_dir = os.getenv("COSYVOICE_MODEL_DIR",
        "/home/liborui/CosyVoice/pretrained_models/CosyVoice-300M-SFT")
    print(f"[初始化] 加载 CosyVoice 模型: {model_dir}")
    init_tts_model(model_dir)
    
    # 指向 backend/data/ 目录
    input_file = os.path.join(backend_dir, "data", "门票.m4a") # 我自己录的音是m4a格式的，换成其他格式应该也能直接处理
    output_file = os.path.join(backend_dir, "data", "temp_audios", "reply_audio.wav")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if not os.path.exists(input_file):
        print(f" 找不到测试音频：{input_file}，请先放一个录音文件进去")
        return

    # 测试 ASR
    print("\n[1/2] 正在听你说话 (ASR) ...")
    t1 = time.time()
    user_text = transcribe_audio(input_file)
    t2 = time.time()

    # 错误拦截防线
    if user_text.startswith("语音识别失败"):
        print(f"识别中断：{user_text}")
        print("停止执行后续的语音生成。")
        return  # 提前结束整个程序，不让它往后走了

    print(f"识别结果: 「{user_text}」 (耗时: {t2-t1:.2f}秒)")

    # 测试 TTS
    print("\n[2/2] 正在生成数字人回复 (TTS) ...")
    reply_text = f"我听清楚了，你刚才说的是：{user_text}。"
    
    t3 = time.time()
    await synthesize_audio(reply_text, output_file)
    t4 = time.time()
    print(f"语音生成完毕，(耗时: {t4-t3:.2f}秒)")

    # 校验生成的 WAV 文件
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", output_file],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        import json
        info = json.loads(result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))
        print(f"[校验] WAV 文件有效，时长: {duration:.2f}秒")
    else:
        print(f"[校验] 警告：无法用 ffprobe 读取 WAV 文件")

    print(f"\n测试成功，可以去 {output_file} 听听结果")

if __name__ == "__main__":
    asyncio.run(main())