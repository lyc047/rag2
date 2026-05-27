"""SQLite数据库配置 —— SQLAlchemy异步引擎"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config.settings import DATABASE_URL

# 确保数据库目录存在
db_dir = os.path.dirname(DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
if db_dir and not os.path.isabs(db_dir):
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    abs_db_dir = project_root / db_dir
    abs_db_dir.parent.mkdir(parents=True, exist_ok=True)

# 创建异步引擎（SQLite需要check_same_thread=False）
engine = create_async_engine(DATABASE_URL, echo=False)

# 异步会话工厂
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM基类"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI依赖 —— 获取数据库会话，请求结束后自动关闭"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库 —— 创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
