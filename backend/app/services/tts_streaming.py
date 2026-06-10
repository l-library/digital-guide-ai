"""TTS 流式播报共享模块：逐句合成 + 严格串行播报

chat.py / websocket.py 共用的 TTS 流式播报基础设施。
设计：TTS 合成并发执行，播报按 LLM 输出顺序严格串行。
"""

import asyncio

import os
import re
import subprocess
import uuid
from app.services.tts_service import synthesize_to_file
from app.services.llm_service import generate_stream_async
from app.services.digital_human_client import get_client as get_dh_client
from app.services.digital_human_session import get_session_id

TEMP_AUDIO_DIR = os.path.abspath(os.path.join("data", "temp_audios"))
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)



def split_sentences(text: str) -> list[str]:
    """按中文标点拆分句子，过滤空串，合并过短片段避免 TTS 质量下降"""
    raw = [s.strip() for s in re.split(r'[。！？\n，；、：]+', text) if s.strip()]
    merged: list[str] = []
    for s in raw:
        # 2 字及以下的片段合并到前一句，避免 TTS 合成质量差
        if merged and len(s) <= 2:
            merged[-1] = merged[-1] + s
        else:
            merged.append(s)
    return merged


def get_wav_duration(filepath: str) -> float:
    """读取 WAV 文件的实际播放时长（秒）。"""
    # 优先：soundfile 直接读 WAV header（无子进程开销）
    try:
        import soundfile as sf
        info = sf.info(filepath)
        if info.duration > 0:
            return info.duration
    except Exception as e:
        print(f"[TTS] soundfile 获取时长失败: {e}")

    # 回退：根据文件大小估算（16-bit mono 22050Hz ≈ 44100 bytes/s）
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



async def synthesize_and_resolve(
    text: str,
    future: asyncio.Future,
    wav_list: list | None = None,
    idx: int | None = None,
):
    """合成 TTS 并将结果设置到 future；future 已在主协程中同步入队

    Args:
        wav_list: 可选，用于跟踪逐句合成的文件名列表
        idx: 可选，当前句子在 wav_list 中的索引
    """
    try:
        audio_filename = await synthesize_to_file(text, TEMP_AUDIO_DIR)
        result = audio_filename if audio_filename else None
        future.set_result(result)
        if wav_list is not None and idx is not None:
            wav_list[idx] = audio_filename
    except Exception as e:
        print(f"[逐句TTS合成失败]: {e}")
        future.set_result(None)



async def _synthesize_single(
    text: str,
    idx: int,
) -> dict | None:
    """合成单句 TTS，返回 {idx, text, audio_filename, duration} 或 None"""
    try:
        audio_filename = await synthesize_to_file(text, TEMP_AUDIO_DIR)
        if not audio_filename:
            return None
        filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
        duration = get_wav_duration(filepath)
        return {
            "idx": idx,
            "text": text,
            "audio_filename": audio_filename,
            "duration": round(duration, 2),
        }
    except Exception as e:
        print(f"[逐句TTS合成失败] idx={idx}: {e}")
        return None


async def create_streaming_pipeline(
    conversation_id: int,
    response_type: int,
    messages_for_llm: list[dict],
):
    """封装 LLM 流式生成 → 句子检测 → TTS 合成的通用流水线（异步生成器）。

    chat.py / websocket.py 通过 async for 迭代消费事件，
    消除重复的流式循环代码。

    生成的事件字典类型：token / sentence / sentence_audio / error / _pipeline_done
    所有事件均包含 conversation_id 字段。
    _pipeline_done 为哨兵事件，包含 full_content / sentence_wavs 元数据。

    Yields:
        dict: {"type": "token", "conversation_id": int, "content": str}
        dict: {"type": "sentence", "conversation_id": int, "content": str, "index": int}
        dict: {"type": "sentence_audio", "conversation_id": int, "index": int,
               "text": str, "audio_filename": str, "duration": float}
        dict: {"type": "error", "conversation_id": int, "message": str}
        dict: {"type": "_pipeline_done", "conversation_id": int, "full_content": str,
               "sentence_wavs": list[str | None]}
    """
    full_content = ""
    sentence_buffer = ""
    tts_tasks: list[tuple[str, int, asyncio.Task]] = []
    idx = 0

    try:
        async for token in generate_stream_async(messages_for_llm):
            full_content += token
            sentence_buffer += token
            yield {
                "type": "token",
                "conversation_id": conversation_id,
                "content": token,
            }

            if sentence_buffer and sentence_buffer[-1] in "。！？\n":
                sentences = split_sentences(sentence_buffer)
                for s in sentences:
                    yield {
                        "type": "sentence",
                        "conversation_id": conversation_id,
                        "content": s,
                        "index": idx,
                    }
                    if response_type == 1:
                        tts_tasks.append(asyncio.create_task(_synthesize_single(s, idx)))
                    idx += 1
                sentence_buffer = ""

        # 处理缓冲区中剩余文本
        if sentence_buffer.strip():
            s = sentence_buffer.strip()
            yield {
                "type": "sentence",
                "conversation_id": conversation_id,
                "content": s,
                "index": idx,
            }
            if response_type == 1:
                tts_tasks.append(asyncio.create_task(_synthesize_single(s, idx)))
            idx += 1

        # Phase 2: 逐个等待 TTS 完成，按序 yield sentence_audio 事件
        # 大部分任务在 LLM 流式期间已完成，await 立即返回
        sentence_wavs: list[str | None] = []
        if tts_tasks:
            for task in tts_tasks:
                try:
                    result = await task
                except Exception as e:
                    print(f"[TTS] synthesis task failed: {e}")
                    sentence_wavs.append(None)
                    continue
                if result is not None:
                    yield {
                        "type": "sentence_audio",
                        "conversation_id": conversation_id,
                        "index": result["idx"],
                        "text": result["text"],
                        "audio_filename": result["audio_filename"],
                        "duration": result["duration"],
                    }
                    sentence_wavs.append(result["audio_filename"])
                else:
                    sentence_wavs.append(None)
        else:
            sentence_wavs = []

    except Exception as e:
        yield {
            "type": "error",
            "conversation_id": conversation_id,
            "message": str(e),
        }
        raise

    yield {
        "type": "_pipeline_done",
        "conversation_id": conversation_id,
        "full_content": full_content,
        "sentence_wavs": sentence_wavs,
    }


def concat_wav_files(wav_paths: list[str], output_dir: str) -> str | None:
    """使用 ffmpeg 无损拼接多个 WAV 文件。

    Args:
        wav_paths: 待拼接的 WAV 文件路径列表（按顺序）
        output_dir: 输出目录

    Returns:
        合并后的文件名，失败返回 None
    """
    valid_paths = [p for p in wav_paths if p and os.path.exists(os.path.join(output_dir, p))]
    if len(valid_paths) < 2:
        return None

    output_filename = f"concat_{uuid.uuid4().hex[:12]}.wav"
    output_path = os.path.join(output_dir, output_filename)

    filelist_path = os.path.join(output_dir, f"filelist_{uuid.uuid4().hex[:8]}.txt")
    try:
        with open(filelist_path, "w", encoding="utf-8") as f:
            for name in valid_paths:
                abs_path = os.path.join(output_dir, name)
                f.write(f"file '{abs_path}'\n")

        result = subprocess.run(
            ["ffmpeg", "-f", "concat", "-safe", "0",
             "-i", filelist_path, "-c", "copy", output_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return output_filename
        else:
            print(f"[concat_wav_files] ffmpeg 拼接失败: {result.stderr}")
            return None
    except FileNotFoundError:
        print("[concat_wav_files] ffmpeg 未找到，无法拼接 WAV")
        return None
    except Exception as e:
        print(f"[concat_wav_files] 异常: {e}")
        return None
    finally:
        if os.path.exists(filelist_path):
            os.remove(filelist_path)
