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
        self._send_queue: Optional[asyncio.Queue] = None
        self._sender_task: Optional[asyncio.Task] = None

    def set_websocket(self, ws):
        """设置 WebSocket 连接（由路由层在 asyncio 上下文中调用）"""
        self._ws = ws
        self._running = ws is not None
        self._loop = asyncio.get_running_loop()
        self._send_queue = asyncio.Queue(maxsize=500)
        self._sender_task = asyncio.ensure_future(self._sender_loop(), loop=self._loop)
        logger.info(f"WebSocketStreamOutput: WebSocket 已设置, running={self._running}")

    def start(self) -> None:
        """启动输出通道"""
        self._running = True
        logger.info("WebSocketStreamOutput: 启动")

    async def _sender_loop(self) -> None:
        """逐帧发送，每次 send 后让出事件循环，消除突发洪峰"""
        while self._running:
            try:
                payload = await asyncio.wait_for(self._send_queue.get(), timeout=1.0)
                if self._ws is not None and not self._ws.closed:
                    await self._ws.send_bytes(payload)
                self._send_queue.task_done()
                await asyncio.sleep(0)  # 让出事件循环，防止连续发送形成突发
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"WebSocket sender_loop 错误: {e}")
                break

    def push_video_frame(self, frame) -> None:
        """
        推送视频帧 — 将 BGR24 numpy 数组编码为 JPEG 并入队发送。

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

            # 入队而非直接发送，满则丢弃（背压）
            try:
                self._send_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

        except Exception as e:
            logger.error(f"WebSocketStreamOutput push_video_frame 错误: {e}")

    def push_audio_frame(self, frame, eventpoint=None) -> None:
        """
        推送音频帧 — 将 int16 PCM 数据入队发送。

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

            # 入队而非直接发送，满则丢弃（背压）
            try:
                self._send_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

        except Exception as e:
            logger.error(f"WebSocketStreamOutput push_audio_frame 错误: {e}")

    def get_buffer_size(self) -> int:
        """返回发送队列中的积压帧数，用于引擎降速限流"""
        if self._send_queue is not None:
            return self._send_queue.qsize()
        return 0

    def stop(self) -> None:
        """停止输出"""
        self._running = False
        if self._sender_task is not None:
            self._sender_task.cancel()
            self._sender_task = None
        logger.info("WebSocketStreamOutput: 停止")