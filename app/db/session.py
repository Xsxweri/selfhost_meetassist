from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# ========== 1. 创建异步引擎 ==========
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # 开发环境打印 SQL 日志，方便调试
    pool_size=10,                 # 连接池常驻连接数
    max_overflow=20,              # 允许临时增加的连接数
    pool_recycle=3600,            # 连接回收时间（秒），防止数据库端超时断开
    pool_pre_ping=True,           # 每次使用前检测连接是否存活
)

# ========== 2. 创建异步会话工厂 ==========
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # commit 后不使对象过期，避免额外查询
    autocommit=False,
    autoflush=False,
)

# ========== 3. ORM 基类（所有模型继承它）==========
class Base(DeclarativeBase):
    pass

# ========== 4. FastAPI 依赖注入：获取 DB Session ==========
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖项，在路由中通过 Depends(get_db) 注入。
    使用 async with 自动管理会话生命周期，异常时自动回滚。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# ========== 5. 应用启动时自动建表（开发阶段用）==========
async def init_db():
    """在 FastAPI lifespan 中调用，自动创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)