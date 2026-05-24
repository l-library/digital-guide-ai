###############################################################################
#  LiveTalking 服务入口 — wav2lip + echo 模式
###############################################################################

import asyncio
from aiohttp import web
from aiohttp_middlewares import cors_middleware

from config import parse_args
import registry
from server.routes import setup_routes
from server.ws_routes import setup_ws_routes
from server.rtc_manager import RTCManager
from server.session_manager import session_manager
from avatars.wav2lip_avatar import load_model, load_avatar, warm_up
from utils.logger import logger

# 全局配置引用，供 build_session 闭包使用
_OPT = None


def build_session(sessionid: str, params: dict):
    """构建 wav2lip avatar 会话（在线程池中执行）"""
    opt = _OPT
    opt.sessionid = sessionid

    model = load_model(opt.modelfile)
    avatar_data = load_avatar(opt.avatar_id)
    avatar = registry.create("avatar", "wav2lip", opt=opt, model=model, avatar=avatar_data)

    from threading import Event, Thread
    quit_event = Event()
    avatar.quit_event = quit_event
    render_thread = Thread(target=avatar.render, args=(quit_event,), daemon=True)
    render_thread.start()

    return avatar


async def on_startup(app):
    """预热 wav2lip 模型"""
    opt = app["opt"]
    model = load_model(opt.modelfile)
    warm_up(opt.batch_size, model, opt.modelres)
    app["wav2lip_model"] = model
    logger.info("Warm-up complete.")


async def on_cleanup(app):
    """关闭时清理 WebRTC 连接"""
    await app["rtc_manager"].shutdown()
    logger.info("LiveTalking service shut down.")


def create_app(opt) -> web.Application:
    """创建 aiohttp 应用"""
    app = web.Application(middlewares=[
        cors_middleware(allow_all=True),
    ])

    app["opt"] = opt
    app["llm_response"] = None

    rtc_manager = RTCManager(opt)
    app["rtc_manager"] = rtc_manager

    setup_routes(app)
    setup_ws_routes(app)
    app.router.add_post("/offer", rtc_manager.handle_offer)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


def main():
    global _OPT

    opt = parse_args()
    _OPT = opt

    import avatars.wav2lip_avatar  # noqa: F401
    import tts.edge                 # noqa: F401
    import streamout.webrtc         # noqa: F401
    import streamout.ws_stream      # noqa: F401

    session_manager.init_builder(build_session)

    app = create_app(opt)
    logger.info(f"LiveTalking service starting on port {opt.listenport}")
    web.run_app(app, port=opt.listenport)


if __name__ == "__main__":
    main()