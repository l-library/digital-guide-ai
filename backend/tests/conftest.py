"""测试配置与共享fixtures。

提供 FastAPI TestClient 和 mock 数字人服务的 fixture，
支持在 digital_human_client 模块创建前后运行测试。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_livetalking():
    """Mock DigitalHumanClient 的所有异步方法，避免真实 HTTP 调用。

    在端点模块级别 patch get_client，返回预配置的 mock 客户端。
    测试可通过 patch 端点级别的其他函数（如 create_digital_human_session）
    来覆盖更具体的行为。

    Yields:
        MagicMock: 包含所有 mock 异步方法的 DigitalHumanClient mock 实例。
    """
    mock_client = MagicMock()
    mock_client.create_session = AsyncMock(return_value={"sessionid": "test-session-123"})
    mock_client.destroy_session = AsyncMock(return_value={"code": 0, "msg": "ok"})
    mock_client.speak = AsyncMock(return_value={"code": 0, "msg": "ok"})
    mock_client.is_speaking = AsyncMock(return_value=False)
    mock_client.interrupt = AsyncMock(return_value={"code": 0, "msg": "ok"})

    from unittest.mock import patch

    with patch(
        "app.api.api_v1.endpoints.digital_human.get_client",
        return_value=mock_client,
    ):
        yield mock_client