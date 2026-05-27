"""FastAPI应用入口 —— 注册路由、中间件、启动事件"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logger import logger
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 —— 启动时初始化数据库，关闭时清理资源"""
    logger.info("===== rag2 启动中 =====")
    await init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("===== rag2 已关闭 =====")


app = FastAPI(title="rag2", version="0.1.0", lifespan=lifespan)

# CORS —— 允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 注册路由 ====================
from app.router.health import router as health_router
from app.router.knowledge import router as knowledge_router
from app.router.chat import router as chat_router
from app.router.note import router as note_router

app.include_router(health_router, tags=["健康检查"])
app.include_router(knowledge_router, prefix="/knowledge", tags=["知识库"])
app.include_router(chat_router, prefix="/chat", tags=["AI助手"])
app.include_router(note_router, prefix="/note", tags=["笔记"])


if __name__ == "__main__":
    import uvicorn
    from app.config.settings import SERVER_PORT
    uvicorn.run("main:app", host="0.0.0.0", port=SERVER_PORT, reload=False)
