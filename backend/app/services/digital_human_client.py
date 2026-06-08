"""异步 HTTP 客户端，用于与 LiveTalking 数字人服务通信。"""

import os

import httpx

LIVETALKING_BASE_URL = os.getenv("LIVETALKING_BASE_URL", "http://localhost:8010")


class DigitalHumanClient:
    """异步 HTTP 客户端，用于与 LiveTalking 服务通信。"""

    def __init__(self, base_url: str = LIVETALKING_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)
        return self._client

    async def create_session(self, sessionid: str | None = None, avatar: str | None = None) -> dict:
        """创建数字人会话，返回 {"sessionid": "..."}"""
        client = await self._get_client()
        payload: dict = {}
        if sessionid is not None:
            payload["sessionid"] = sessionid
        if avatar is not None:
            payload["avatar"] = avatar
        resp = await client.post("/api/admin/session", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"LiveTalking create_session 失败: {data.get('msg')}")
        return data.get("data", {})

    async def destroy_session(self, sessionid: str) -> dict:
        """销毁数字人会话"""
        client = await self._get_client()
        resp = await client.delete(f"/api/admin/session/{sessionid}")
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"LiveTalking destroy_session 失败: {data.get('msg')}")
        return data

    async def speak(self, sessionid: str, text: str) -> dict:
        """驱动数字人播报文本（echo 模式）"""
        client = await self._get_client()
        payload = {"sessionid": sessionid, "type": "echo", "text": text}
        resp = await client.post("/human", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"LiveTalking speak 失败: {data.get('msg')}")
        return data

    async def is_speaking(self, sessionid: str) -> bool:
        """查询数字人是否正在说话"""
        client = await self._get_client()
        payload = {"sessionid": sessionid}
        resp = await client.post("/is_speaking", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return bool(data.get("data", False))

    async def interrupt(self, sessionid: str) -> dict:
        """打断当前播报"""
        client = await self._get_client()
        payload = {"sessionid": sessionid}
        resp = await client.post("/interrupt_talk", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"LiveTalking interrupt 失败: {data.get('msg')}")
        return data

    async def send_audio(self, sessionid: str, audio_bytes: bytes, filename: str = "audio.wav") -> dict:
        """上传音频文件到 LiveTalking，驱动口型动画和音视频帧推送"""
        client = await self._get_client()
        files = {"file": (filename, audio_bytes, "audio/wav")}
        data = {"sessionid": sessionid}
        resp = await client.post("/humanaudio", data=data, files=files)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"LiveTalking send_audio 失败: {result.get('msg')}")
        return result

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# 模块级单例
_client: DigitalHumanClient | None = None


def get_client() -> DigitalHumanClient:
    """获取全局 DigitalHumanClient 单例（懒加载）。"""
    global _client
    if _client is None:
        _client = DigitalHumanClient()
    return _client
