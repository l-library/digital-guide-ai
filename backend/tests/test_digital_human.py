"""数字人 API 端点集成测试。

7 个测试覆盖：会话创建、播报、打断、状态查询、会话销毁。
使用 mock 替代真实的 LiveTalking 服务，无需外部依赖。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCreateSession:
    """POST /api/v1/digital-human/session — 创建数字人会话。"""

    def test_create_session(self, client, mock_livetalking):
        """提交有效 conversation_id，断言返回 200 + session_id。"""
        with patch(
            "app.api.api_v1.endpoints.digital_human.create_digital_human_session",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = "test-session-abc"
            resp = client.post(
                "/api/v1/digital-human/session",
                json={"conversation_id": 1},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 200
            assert data["data"]["session_id"] == "test-session-abc"
            assert data["data"]["conversation_id"] == 1
            mock_create.assert_awaited_once_with(1)

    def test_create_session_missing_conversation_id(self, client, mock_livetalking):
        """未传 conversation_id，断言 Pydantic 422 校验失败。"""
        resp = client.post("/api/v1/digital-human/session", json={})
        assert resp.status_code == 422


class TestSpeak:
    """POST /api/v1/digital-human/speak — 驱动数字人播报。"""

    def test_speak(self, client, mock_livetalking):
        """提交有效 session，断言返回 200。"""
        with patch(
            "app.api.api_v1.endpoints.digital_human.get_session_id",
            return_value="test-session-abc",
        ):
            resp = client.post(
                "/api/v1/digital-human/speak",
                json={"conversation_id": 1, "text": "欢迎来到景区"},
            )
            assert resp.status_code == 200
            assert resp.json()["code"] == 200
            mock_livetalking.speak.assert_awaited_once_with(
                "test-session-abc", "欢迎来到景区"
            )

    def test_speak_invalid_session(self, client, mock_livetalking):
        """提交不存在的 conversation_id，断言 JSON code=404。"""
        with patch(
            "app.api.api_v1.endpoints.digital_human.get_session_id",
            return_value=None,
        ):
            resp = client.post(
                "/api/v1/digital-human/speak",
                json={"conversation_id": 999, "text": "你好"},
            )
            assert resp.status_code == 200
            assert resp.json()["code"] == 404


class TestInterrupt:
    """POST /api/v1/digital-human/interrupt — 打断当前播报。"""

    def test_interrupt(self, client, mock_livetalking):
        """提交有效 session，断言返回 200。"""
        with patch(
            "app.api.api_v1.endpoints.digital_human.get_session_id",
            return_value="test-session-abc",
        ):
            resp = client.post(
                "/api/v1/digital-human/interrupt",
                json={"conversation_id": 1},
            )
            assert resp.status_code == 200
            assert resp.json()["code"] == 200
            mock_livetalking.interrupt.assert_awaited_once_with("test-session-abc")


class TestStatus:
    """GET /api/v1/digital-human/status/{id} — 查询数字人状态。"""

    def test_status(self, client, mock_livetalking):
        """提交有效 session，断言返回 200 + is_speaking 字段。"""
        mock_livetalking.is_speaking = AsyncMock(return_value=True)

        with patch(
            "app.api.api_v1.endpoints.digital_human.get_session_id",
            return_value="test-session-abc",
        ):
            resp = client.get("/api/v1/digital-human/status/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 200
            assert "is_speaking" in data["data"]
            assert data["data"]["is_speaking"] is True
            mock_livetalking.is_speaking.assert_awaited_once_with("test-session-abc")


class TestDestroySession:
    """DELETE /api/v1/digital-human/session/{id} — 销毁数字人会话。"""

    def test_destroy_session(self, client, mock_livetalking):
        """销毁有效会话，断言返回 200。"""
        with patch(
            "app.api.api_v1.endpoints.digital_human.destroy_session",
            new_callable=AsyncMock,
        ) as mock_destroy:
            mock_destroy.return_value = True
            resp = client.delete("/api/v1/digital-human/session/1")
            assert resp.status_code == 200
            assert resp.json()["code"] == 200
            mock_destroy.assert_awaited_once_with(1)