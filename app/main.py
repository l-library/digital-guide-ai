from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.api_v1.api import api_router

# 1. 定义生命周期（预热逻辑）
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在预热RAG服务，加载embedding模型...")
    from app.services.rag_service import _get_stores
    _get_stores()
    print("预热完成，服务就绪。")
    yield   # FastAPI 开始接受请求
    print("服务关闭。")

# 2. 实例化应用（把生命周期挂进来）
app = FastAPI(
    title="A5景区数字人 - 后端 API",
    lifespan=lifespan,
)

# 3. 接入所有业务路由
app.include_router(api_router, prefix="/api/v1")

# 4. 健康检查接口
@app.get("/")
def check_health():
    return {"status": "ok", "message": "数字人服务已成功启动，模型已就绪!"}