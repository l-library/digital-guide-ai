###############################################################################
#  Output — WebSocket JPEG 帧流输出
#
#  通过 aiohttp WebSocket 向客户端实时推送 JPEG 视频帧 + PCM 音频数据，
#  替代完整 WebRTC 栈，适用于 Qt/QML 等原生客户端。
###############################################################################

import asyncio
import cv2
import numpy as np
from typing import Optional, TYPE_CHECKING

from streamout.base_output import BaseOutput
from registry import register
from utils.logger import logger

if TYPE_CHECKING:
    from avatars.base_avatar import BaseAvatar


@register("streamout", "ws_stream")
class WebSocketStreamOutput(BaseOutput):
    """WebSocket 帧流输出 — JPEG 视频 + PCM 音频"""

    def __init__(self, opt=None, parent: Optional['BaseAvatar'] = None, **kwargs):
        super().__init__(opt, parent)
        self._ws = None
        self._loop = None
        self._running = False
        self._jpeg_quality = 75
        self._frame_count = 0

    def set_websocket(self, ws):
        """设置 WebSocket 连接（由路由层在 asyncio 上下文中调用）"""
        self._ws = ws
        self._running = ws is not None
        self._loop = asyncio.get_running_loop()
        logger.info(f"WebSocketStreamOutput: WebSocket 已设置, running={self._running}")

    def start(self) -> None:
        """启动输出通道"""
        self._running = True
        logger.info("WebSocketStreamOutput: 启动")

    def push_video_frame(self, frame) -> None:
        """
        推送视频帧 — 将 BGR24 numpy 数组编码为 JPEG 并通过 WebSocket 发送。

        帧格式: 二进制帧，前4字节为类型标识 (0x01 = video)，
                后4字节为帧序号，其余为 JPEG 数据。
        """
        if not self._running or self._ws is None or self._loop is None:
            return

        try:
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality]
            success, jpeg_data = cv2.imencode('.jpg', frame, encode_param)
            if not success:
                return

            header = b'\x01' + self._frame_count.to_bytes(4, byteorder='big')
            self._frame_count += 1
            payload = header + jpeg_data.tobytes()

            self._loop.call_soon_threadsafe(
                lambda p=payload: asyncio.ensure_future(self._send_binary(p), loop=self._loop)
            )

        except Exception as e:
            logger.error(f"WebSocketStreamOutput push_video_frame 错误: {e}")

    def push_audio_frame(self, frame, eventpoint=None) -> None:
        """
        推送音频帧 — 将 int16 PCM 数据通过 WebSocket 发送。

        帧格式: 二进制帧，前4字节为类型标识 (0x02 = audio)，
                后1字节为 eventpoint 类型，其余为 PCM 数据。
        """
        if not self._running or self._ws is None or self._loop is None:
            return

        try:
            ep_code = 0
            if eventpoint:
                status = eventpoint.get('status', '')
                if status == 'start':
                    ep_code = 1
                elif status == 'end':
                    ep_code = 2

            header = b'\x02' + ep_code.to_bytes(1, byteorder='big')
            payload = header + frame.tobytes()

            self._loop.call_soon_threadsafe(
                lambda p=payload: asyncio.ensure_future(self._send_binary(p), loop=self._loop)
            )

        except Exception as e:
            logger.error(f"WebSocketStreamOutput push_audio_frame 错误: {e}")

    async def _send_binary(self, payload: bytes) -> None:
        """异步发送二进制数据到 WebSocket"""
        if self._ws is not None and not self._ws.closed:
            try:
                await self._ws.send_bytes(payload)
            except Exception as e:
                logger.error(f"WebSocket 发送错误: {e}")
                self._running = False

    def get_buffer_size(self) -> int:
        """WebSocket 输出无缓冲队列"""
        return 0

    def stop(self) -> None:
        """停止输出"""
        self._running = False
        logger.info("WebSocketStreamOutput: 停止")