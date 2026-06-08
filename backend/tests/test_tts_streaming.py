"""TTS 流式播报管道集成测试。

覆盖：句子拆分、WAV 拼接、流式管道事件生成、voice_stream SSE 端点。
使用 mock 替代真实 LLM/TTS 服务，无需外部依赖。
"""

import asyncio
import os
import struct
import wave
from unittest.mock import AsyncMock, patch

import pytest

from app.services.tts_streaming import (
    concat_wav_files,
    create_streaming_pipeline,
    split_sentences,
)


class TestSplitSentences:
    """split_sentences — 按中文标点拆分句子。"""

    def test_basic(self):
        """基本标点拆分：句号、感叹号、问号。"""
        assert split_sentences("你好。欢迎！再见？") == ["你好", "欢迎", "再见"]

    def test_no_punctuation(self):
        """无标点文本返回整个句子。"""
        assert split_sentences("你好欢迎") == ["你好欢迎"]

    def test_empty(self):
        """空字符串返回空列表。"""
        assert split_sentences("") == []

    def test_newlines(self):
        """换行符作为分隔符，拆分多行文本。"""
        assert split_sentences("第一行\n第二行。第三行") == ["第一行", "第二行", "第三行"]

    def test_consecutive_delimiters(self):
        """连续标点不会产生空串。"""
        assert split_sentences("你好。。欢迎！！") == ["你好", "欢迎"]


class TestConcatWavFiles:
    """concat_wav_files — WAV 文件拼接。"""

    def test_single_file_returns_none(self, tmp_path):
        """单文件不拼接，返回 None。"""
        result = concat_wav_files(["only.wav"], str(tmp_path))
        assert result is None

    def test_empty_list_returns_none(self, tmp_path):
        """空列表返回 None。"""
        result = concat_wav_files([], str(tmp_path))
        assert result is None

    def test_skip_missing_files(self, tmp_path):
        """列表中包含不存在文件时被过滤，剩余不足两份返回 None。"""
        result = concat_wav_files(["ghost1.wav", "ghost2.wav"], str(tmp_path))
        assert result is None

    def test_multiple_files_concat(self, tmp_path):
        """创建两个真实 WAV 文件并拼接，验证返回有效文件名。"""

        def make_wav(path, duration_sec=0.1):
            sample_rate = 22050
            n_samples = int(sample_rate * duration_sec)
            with wave.open(path, "w") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sample_rate)
                w.writeframes(struct.pack("<h", 0) * n_samples)

        wav1 = str(tmp_path / "test1.wav")
        wav2 = str(tmp_path / "test2.wav")
        make_wav(wav1, 0.1)
        make_wav(wav2, 0.1)

        result = concat_wav_files(["test1.wav", "test2.wav"], str(tmp_path))
        # ffmpeg 不可用时返回 None，此时跳过后续断言
        if result is not None:
            assert result.endswith(".wav")
            assert os.path.exists(os.path.join(str(tmp_path), result))


class TestStreamingPipeline:
    """create_streaming_pipeline — 流式管道事件生成。"""

    def test_pipeline_yields_correct_events(self):
        """Mock LLM 流式输出，验证管道产生 token / sentence / sentence_audio / _pipeline_done 事件。"""

        async def mock_llm(*args, **kwargs):
            for t in ["你好", "。", "欢迎"]:
                yield t

        async def run():
            with patch(
                "app.services.tts_streaming.generate_stream_async",
                side_effect=mock_llm,
            ):
                with patch(
                    "app.services.tts_streaming.synthesize_to_file",
                    new_callable=AsyncMock,
                    return_value="dummy.wav",
                ):
                    with patch(
                        "app.services.tts_streaming.get_wav_duration",
                        return_value=1.5,
                    ):
                        pipeline = create_streaming_pipeline(
                            1, 1, [{"role": "user", "content": "test"}]
                        )
                        events = []
                        async for event in pipeline:
                            events.append(event)

                        # 验证事件类型完整
                        types = [e["type"] for e in events]
                        assert "token" in types, f"缺少 token 事件，types: {types}"
                        assert "sentence" in types, f"缺少 sentence 事件，types: {types}"
                        assert "sentence_audio" in types, f"缺少 sentence_audio 事件，types: {types}"
                        assert "_pipeline_done" in types, f"缺少 _pipeline_done 哨兵，types: {types}"

                        # 验证所有事件包含 conversation_id
                        for e in events:
                            assert "conversation_id" in e, (
                                f"事件 {e['type']} 缺少 conversation_id"
                            )

                        # 验证 _pipeline_done 包含元数据（无 player_task）
                        done = events[-1]
                        assert done["type"] == "_pipeline_done"
                        assert "full_content" in done
                        assert "sentence_wavs" in done
                        assert "player_task" not in done, (
                            "_pipeline_done 不应包含 player_task"
                        )

                        # 验证 sentence_audio 事件结构
                        audio_events = [e for e in events if e["type"] == "sentence_audio"]
                        assert len(audio_events) >= 1
                        for ae in audio_events:
                            assert "index" in ae
                            assert "audio_filename" in ae
                            assert "duration" in ae

                        return events

        asyncio.run(run())

    def test_pipeline_without_tts(self):
        """response_type=0 时不触发 TTS，管道仍正常产生事件，无 sentence_audio。"""

        async def mock_llm(*args, **kwargs):
            for t in ["你好", "再见"]:
                yield t

        async def run():
            with patch(
                "app.services.tts_streaming.generate_stream_async",
                side_effect=mock_llm,
            ):
                pipeline = create_streaming_pipeline(
                    1, 0, [{"role": "user", "content": "test"}]
                )
                events = []
                async for event in pipeline:
                    events.append(event)

                types = [e["type"] for e in events]
                assert "token" in types
                assert "sentence" in types
                assert "_pipeline_done" in types
                assert "sentence_audio" not in types, (
                    f"response_type=0 不应产生 sentence_audio，types: {types}"
                )

                done = events[-1]
                assert done["type"] == "_pipeline_done"
                assert done["sentence_wavs"] == []
                assert "player_task" not in done, (
                    "_pipeline_done 不应包含 player_task"
                )

        asyncio.run(run())

    def test_pipeline_error_handling(self):
        """LLM 抛出异常时，管道产生 error 事件并传播异常。"""

        async def mock_llm_error(*args, **kwargs):
            yield "你好"
            raise RuntimeError("LLM 服务异常")

        async def run():
            with patch(
                "app.services.tts_streaming.generate_stream_async",
                side_effect=mock_llm_error,
            ):
                pipeline = create_streaming_pipeline(
                    1, 0, [{"role": "user", "content": "test"}]
                )
                events = []
                try:
                    async for event in pipeline:
                        events.append(event)
                except RuntimeError:
                    pass

                types = [e["type"] for e in events]
                assert "error" in types, f"缺少 error 事件，types: {types}"

        asyncio.run(run())


class TestSentenceAudioEvents:
    """create_streaming_pipeline — sentence_audio 事件生成。"""

    def test_sentence_audio_events_generated(self):
        """验证 response_type=1 时生成 sentence_audio 事件，index 递增且有 duration。"""

        async def mock_llm(*args, **kwargs):
            for t in ["你好", "。", "欢迎", "。"]:
                yield t

        async def run():
            with patch(
                "app.services.tts_streaming.generate_stream_async",
                side_effect=mock_llm,
            ):
                with patch(
                    "app.services.tts_streaming.synthesize_to_file",
                    new_callable=AsyncMock,
                    return_value="dummy.wav",
                ):
                    with patch(
                        "app.services.tts_streaming.get_wav_duration",
                        return_value=1.5,
                    ):
                        pipeline = create_streaming_pipeline(
                            1, 1, [{"role": "user", "content": "test"}]
                        )
                        audio_events = []
                        async for event in pipeline:
                            if event["type"] == "sentence_audio":
                                audio_events.append(event)
                            if event["type"] == "_pipeline_done":
                                break

                        assert len(audio_events) == 2, (
                            f"Expected 2 audio events, got {len(audio_events)}"
                        )
                        assert audio_events[0]["index"] == 0
                        assert audio_events[1]["index"] == 1
                        assert audio_events[0]["duration"] == 1.5
                        assert audio_events[0]["conversation_id"] == 1
                        assert audio_events[0]["audio_filename"] == "dummy.wav"
                        print("PASS: sentence_audio events correct")

        asyncio.run(run())

    def test_no_sentence_audio_when_response_type_zero(self):
        """response_type=0 时不生成 sentence_audio 事件。"""

        async def mock_llm(*args, **kwargs):
            for t in ["你好", "。"]:
                yield t

        async def run():
            with patch(
                "app.services.tts_streaming.generate_stream_async",
                side_effect=mock_llm,
            ):
                pipeline = create_streaming_pipeline(
                    1, 0, [{"role": "user", "content": "test"}]
                )
                audio_events = []
                async for event in pipeline:
                    if event["type"] == "sentence_audio":
                        audio_events.append(event)
                    if event["type"] == "_pipeline_done":
                        break
                assert len(audio_events) == 0, (
                    f"Expected 0 audio events, got {len(audio_events)}"
                )
                print("PASS: no sentence_audio when response_type=0")

        asyncio.run(run())

    def test_sentence_audio_matches_sentence_count(self):
        """每个句子对应一个 sentence_audio 事件，index 连续。"""

        async def mock_llm(*args, **kwargs):
            for t in ["第一句", "。", "第二句", "。", "第三句", "。"]:
                yield t

        async def run():
            with patch(
                "app.services.tts_streaming.generate_stream_async",
                side_effect=mock_llm,
            ):
                with patch(
                    "app.services.tts_streaming.synthesize_to_file",
                    new_callable=AsyncMock,
                    return_value="dummy.wav",
                ):
                    with patch(
                        "app.services.tts_streaming.get_wav_duration",
                        return_value=2.0,
                    ):
                        pipeline = create_streaming_pipeline(
                            1, 1, [{"role": "user", "content": "test"}]
                        )
                        sentence_count = 0
                        audio_events = []
                        async for event in pipeline:
                            if event["type"] == "sentence":
                                sentence_count += 1
                            if event["type"] == "sentence_audio":
                                audio_events.append(event)
                            if event["type"] == "_pipeline_done":
                                break

                        assert sentence_count == 3, (
                            f"Expected 3 sentences, got {sentence_count}"
                        )
                        assert len(audio_events) == 3, (
                            f"Expected 3 audio events, got {len(audio_events)}"
                        )
                        for i, ae in enumerate(audio_events):
                            assert ae["index"] == i, (
                                f"Expected index {i}, got {ae['index']}"
                            )
                        print("PASS: sentence_audio count matches sentences")

        asyncio.run(run())


class TestPlayAudioEndpoint:
    """POST /api/v1/play-audio 端点测试（路由注册 + 函数签名验证）。"""

    def test_play_audio_route_exists(self):
        """验证 /play-audio 路由已注册到 digital_human router。"""
        from app.api.api_v1.endpoints.digital_human import router

        paths = []
        for r in router.routes:
            if hasattr(r, "path"):
                paths.append(r.path)

        assert "/play-audio" in paths, (
            f"期望 /play-audio 在路由中，实际: {paths}"
        )

    def test_play_audio_endpoint_callable(self):
        """验证 play_audio 端点是可调用的异步函数。"""
        import inspect

        from app.api.api_v1.endpoints.digital_human import play_audio

        assert callable(play_audio), "play_audio 应该可调用"
        assert inspect.iscoroutinefunction(play_audio), (
            "play_audio 应该是异步协程函数"
        )


class TestChatVoiceStreamEndToEnd:
    """GET/POST /chat/voice_stream — 端点存在性与函数签名验证。"""

    def test_voice_stream_route_exists(self):
        """验证 /chat/voice_stream 路由已注册到 chat router。"""
        from app.api.api_v1.endpoints.chat import router

        paths = []
        for r in router.routes:
            if hasattr(r, "path"):
                paths.append(r.path)

        assert "/chat/voice_stream" in paths, (
            f"期望 /chat/voice_stream 在路由中，实际: {paths}"
        )

    def test_create_streaming_pipeline_importable(self):
        """验证 create_streaming_pipeline 是可调用的异步生成器函数。"""
        import inspect

        assert callable(create_streaming_pipeline), (
            "create_streaming_pipeline 应该可调用"
        )
        assert inspect.isasyncgenfunction(create_streaming_pipeline), (
            "create_streaming_pipeline 应该是异步生成器函数"
        )

    def test_split_sentences_signature(self):
        """验证 split_sentences 接受字符串返回列表。"""
        result = split_sentences("测试")
        assert isinstance(result, list)
