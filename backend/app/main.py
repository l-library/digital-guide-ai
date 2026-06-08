from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.api_v1.api import api_router
from app.api.api_v1.endpoints.websocket import router as ws_router
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在初始化数据库...")
    from app.database import init_db
    init_db()
    print("数据库就绪。")

    print("正在预热RAG服务，加载embedding模型...")
    from app.services.rag_service import _get_stores
    _get_stores()
    print("预热完成，服务就绪。")

    print("正在同步预摄入文档到数据库...")
    from app.services.knowledge_service import sync_pre_ingested_docs
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        sync_pre_ingested_docs(db)
    finally:
        db.close()
    print("预摄入文档同步完成。")

    print("正在预热ASR服务，加载Whisper模型...")
    from app.services.asr_service import _get_model
    import asyncio
    await asyncio.to_thread(_get_model)
    print("ASR服务就绪。")

    print("正在预热TTS服务，加载CosyVoice模型...")
    from app.services.tts_service import init_tts_model
    cosyvoice_dir = os.getenv("COSYVOICE_MODEL_DIR",
        "/home/liborui/CosyVoice/pretrained_models/CosyVoice-300M-SFT")
    try:
        init_tts_model(cosyvoice_dir)
        print("CosyVoice 模型加载完成")
    except Exception as e:
        print(f"[启动] CosyVoice 模型加载失败（TTS 不可用）: {e}")

    yield
    print("服务关闭。")


app = FastAPI(
    title="A5景区数字人 - 后端 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/")
def check_health():
    return {"status": "ok", "message": "数字人服务已成功启动，模型已就绪!"}
