"""TTS 流式播报共享模块：逐句合成 + 即时交付

chat.py / websocket.py 共用的 TTS 流式播报基础设施。
设计：TTS 合成与 LLM 流式并行执行，合成完成后 sentence_audio 事件
在 LLM 生成期间即流式 yield 给前端，前端无需等待 LLM 全部生成完。
"""

import asyncio

import os
import re
import subprocess
import time
import uuid
from app.services.tts_service import synthesize_to_file
from app.services.llm_service import generate_stream_async
from app.services.digital_human_client import get_client as get_dh_client
from app.services.digital_human_session import get_session_id

TEMP_AUDIO_DIR = os.path.abspath(os.path.join("data", "temp_audios"))
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)



def split_sentences(text: str) -> list[str]:
    """按中文标点拆分句子，过滤空串。

    分句策略（最小长度混合分句）：
    - 句末标点（。！？\n）：总是分句，无论句子长度
    - 逗分标点（，；）：仅当当前累积片段 > 8 字时才分句

    这样短句（如"您好，欢迎来到祥符禅寺景区"）保持完整，
    避免 0.3s 的微型音频碎片（LiveTalking 每个文件有 ~0.7s 固定开销）；
    长句在逗号处拆分为 4-5s 的中等句，TTS 合成更快，
    更容易在前一句播放期间完成 → 预推送成功率更高。
    """
    SENTENCE_END = set("。！？\n")
    COMMA = set("，；")
    MIN_LENGTH = 8

    fragments: list[str] = []
    current = ""

    for ch in text:
        if ch in SENTENCE_END:
            current = current.strip()
            if current:
                fragments.append(current)
            current = ""
        elif ch in COMMA:
            current += ch
            # 逗号处分句：仅当当前片段超过最小长度时
            if len(current) > MIN_LENGTH:
                current = current.strip()
                if current:
                    fragments.append(current)
                current = ""
        else:
            current += ch

    # 处理末尾未闭合的片段
    current = current.strip()
    if current:
        fragments.append(current)

    return fragments


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
    t0 = time.monotonic()
    try:
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        t_read = time.monotonic()
        await get_dh_client().send_audio(sessionid, audio_bytes)
        t_push = time.monotonic()
        print(
            f"[LiveTalking推送] conv={conversation_id} "
            f"文件读取={t_read - t0:.3f}s LiveTalking POST={t_push - t_read:.3f}s "
            f"总耗时={t_push - t0:.3f}s"
        )
    except Exception as e:
        print(f"[LiveTalking音频推送失败] conversation_id={conversation_id}: {e}")


async def send_audio_to_livetalking_queued(conversation_id: int, audio_filename: str):
    """预推送：将 WAV 暂存到 LiveTalking 待处理队列，不立即推理。

    LiveTalking 会将音频存入内部缓冲区，等 /flush_queue 调用后再开始推理。
    """
    sessionid = get_session_id(conversation_id)
    if sessionid is None:
        return
    filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
    if not os.path.exists(filepath):
        return
    t0 = time.monotonic()
    try:
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        t_read = time.monotonic()
        await get_dh_client().send_audio_queued(sessionid, audio_bytes)
        t_push = time.monotonic()
        print(
            f"[LiveTalking预推送队列] conv={conversation_id} "
            f"文件读取={t_read - t0:.3f}s LiveTalking POST={t_push - t_read:.3f}s "
            f"总耗时={t_push - t0:.3f}s"
        )
    except Exception as e:
        print(f"[LiveTalking预推送队列失败] conversation_id={conversation_id}: {e}")


async def flush_livetalking_queue(conversation_id: int):
    """通知 LiveTalking 将待处理队列中的下一句音频推入推理管道。"""
    sessionid = get_session_id(conversation_id)
    if sessionid is None:
        return
    try:
        await get_dh_client().flush_audio_queue(sessionid)
    except Exception as e:
        print(f"[flush-livetalking] conv={conversation_id} 失败: {e}")



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



async def create_streaming_pipeline(
    conversation_id: int,
    response_type: int,
    messages_for_llm: list[dict],
):
    """封装 LLM 流式生成 → 句子检测 → TTS 合成的通用流水线（异步生成器）。

    chat.py / websocket.py 通过 async for 迭代消费事件，
    消除重复的流式循环代码。

    TTS 合成与 LLM 流式并行：句子检测后立即 asyncio.create_task 启动 TTS，
    TTS 完成后 sentence_audio 事件在 LLM 生成期间就流式 yield 给前端，
    前端无需等待 LLM 全部生成完即可开始播放第一句音频。

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
    tts_tasks: list[asyncio.Task] = []
    tts_results: dict[int, dict | None] = {}
    next_yield_idx = 0
    sentence_wavs: list[str | None] = []
    idx = 0
    pipeline_start = time.monotonic()

    async def _synthesize_and_store(text: str, task_idx: int):
        """合成单句 TTS，结果存入 tts_results 字典供主循环按序 yield"""
        try:
            audio_filename = await synthesize_to_file(text, TEMP_AUDIO_DIR)
            if not audio_filename:
                tts_results[task_idx] = None
                return
            filepath = os.path.join(TEMP_AUDIO_DIR, audio_filename)
            duration = get_wav_duration(filepath)
            tts_results[task_idx] = {
                "idx": task_idx,
                "text": text,
                "audio_filename": audio_filename,
                "duration": round(duration, 2),
            }
        except Exception as e:
            print(f"[逐句TTS合成失败] idx={task_idx}: {e}")
            tts_results[task_idx] = None

    def _drain_completed() -> list[dict]:
        """按序提取已完成的 TTS 结果，组装 sentence_audio 事件列表（非阻塞）"""
        nonlocal next_yield_idx
        events: list[dict] = []
        while next_yield_idx in tts_results:
            result = tts_results.pop(next_yield_idx)
            if result is not None:
                events.append({
                    "type": "sentence_audio",
                    "conversation_id": conversation_id,
                    "index": result["idx"],
                    "text": result["text"],
                    "audio_filename": result["audio_filename"],
                    "duration": result["duration"],
                })
                sentence_wavs.append(result["audio_filename"])
            else:
                sentence_wavs.append(None)
            next_yield_idx += 1
        return events

    try:
        async for token in generate_stream_async(messages_for_llm):
            full_content += token
            sentence_buffer += token
            yield {
                "type": "token",
                "conversation_id": conversation_id,
                "content": token,
            }

            if sentence_buffer and sentence_buffer[-1] in "。！？\n，；":
                sentences = split_sentences(sentence_buffer)
                for s in sentences:
                    yield {
                        "type": "sentence",
                        "conversation_id": conversation_id,
                        "content": s,
                        "index": idx,
                    }
                    if response_type == 1:
                        tts_tasks.append(
                            asyncio.create_task(_synthesize_and_store(s, idx))
                        )
                    idx += 1
                sentence_buffer = ""

            # 流式交付：LLM 生成期间，按序 yield 已完成的 TTS 音频
            # 前端无需等待 LLM 全部生成完即可开始播放
            if response_type == 1:
                for event in _drain_completed():
                    elapsed = time.monotonic() - pipeline_start
                    print(
                        f"[TTS流式] 句{event['index']}音频已交付，"
                        f"耗时 {elapsed:.2f}s（pipeline 启动至今）"
                    )
                    yield event

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
                tts_tasks.append(asyncio.create_task(_synthesize_and_store(s, idx)))
            idx += 1

        # LLM 结束后，逐个等待 TTS 完成，按序 yield
        # 用 asyncio.wait(FIRST_COMPLETED) 而非 gather，避免等待所有任务
        # 才交付——先完成的先交付给前端
        if tts_tasks:
            pending = set(tts_tasks)
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for event in _drain_completed():
                    elapsed = time.monotonic() - pipeline_start
                    print(
                        f"[TTS流式] 句{event['index']}音频已交付（LLM结束后），"
                        f"耗时 {elapsed:.2f}s"
                    )
                    yield event

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
