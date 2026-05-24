###############################################################################
#  WebSocket 流路由 — 实时视频帧推送
###############################################################################

import json
import asyncio
from aiohttp import web, WSMsgType

from server.session_manager import session_manager
from utils.logger import logger


async def ws_stream(request):
    """
    WebSocket 端点 — 客户端连接后接收实时 JPEG 视频帧 + PCM 音频。

    连接流程:
    1. 客户端连接 ws://host:port/ws_stream
    2. 可选: 发送 JSON {"type":"bind", "sessionid":"xxx"} 绑定已存在的会话
    3. 如果未绑定, 自动创建新会话
    4. 服务器开始推送视频/音频二进制帧
    5. 客户端可发送 JSON 消息: {"type":"text", "text":"你好"} 触发数字人说话
    """

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    sessionid = None
    avatar_session = None
    ws_output = None

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get('type', '')
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"ws_stream: 无效的 JSON 消息: {msg.data}")
                    continue

                if msg_type == 'bind':
                    # 绑定到已有会话
                    sessionid = data.get('sessionid', '')
                    avatar_session = session_manager.get_session(sessionid)
                    if avatar_session is None:
                        await ws.send_json({'type': 'error', 'message': 'session not found'})
                        continue

                    # 替换 avatar output 为 ws_stream
                    from streamout.ws_stream import WebSocketStreamOutput
                    ws_output = WebSocketStreamOutput(opt=avatar_session.opt, parent=avatar_session)
                    avatar_session.output = ws_output
                    ws_output.set_websocket(ws)
                    ws_output.start()
                    logger.info(f"ws_stream: 绑定到已有会话 {sessionid}")

                    await ws.send_json({'type': 'bound', 'sessionid': sessionid})

                elif msg_type == 'text':
                    # 文本输入 — 让数字人说话
                    if avatar_session is None:
                        await ws.send_json({'type': 'error', 'message': 'not bound to a session'})
                        continue

                    text = data.get('text', '')
                    tts_info = data.get('tts', {})
                    avatar_session.put_msg_txt(text, tts_info)
                    await ws.send_json({'type': 'text_ack', 'text': text})

                elif msg_type == 'interrupt':
                    if avatar_session is not None:
                        avatar_session.flush_talk()
                        await ws.send_json({'type': 'interrupt_ack'})

                elif msg_type == 'create':
                    # 创建新会话
                    sessionid = await session_manager.create_session(data)
                    avatar_session = session_manager.get_session(sessionid)

                    from streamout.ws_stream import WebSocketStreamOutput
                    ws_output = WebSocketStreamOutput(opt=avatar_session.opt, parent=avatar_session)
                    avatar_session.output = ws_output
                    ws_output.set_websocket(ws)
                    ws_output.start()
                    logger.info(f"ws_stream: 创建新会话 {sessionid}")

                    await ws.send_json({'type': 'created', 'sessionid': sessionid})

            elif msg.type == WSMsgType.ERROR:
                logger.error(f"ws_stream: WebSocket 错误: {ws.exception()}")
                break

    except Exception as e:
        logger.error(f"ws_stream: 异常: {e}")
    finally:
        # 清理
        if ws_output is not None:
            ws_output.stop()
        if sessionid and avatar_session:
            # 恢复原始 webrtc output
            try:
                from streamout.webrtc import WebRTCOutput
                avatar_session.output = WebRTCOutput(opt=avatar_session.opt, parent=avatar_session)
            except Exception:
                pass
        logger.info(f"ws_stream: WebSocket 连接关闭, sessionid={sessionid}")

    return ws


def setup_ws_routes(app):
    """注册 WebSocket 流路由"""
    app.router.add_get("/ws_stream", ws_stream)