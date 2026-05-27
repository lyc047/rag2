"""健康检查路由"""
from fastapi import APIRouter
from app.core.response import success_response

router = APIRouter()


@router.get("/health/live")
async def health_live():
    """存活检查"""
    return success_response(data={"status": "ok"})


@router.get("/health/ready")
async def health_ready():
    """就绪检查 —— 验证数据库连接"""
    from app.db.database import engine
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return success_response(data={"status": "ready"})
    except Exception as e:
        return success_response(data={"status": "not_ready", "error": str(e)})
