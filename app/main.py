from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1 import meetings, auth, consents, stream, summaries, audit, shares, exports, tasks, search, agent

from app.core.config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 表结构统一由 alembic 管理，启动不再自动 create_all
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="AI 驱动的会议助理",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(consents.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")
app.include_router(summaries.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(shares.router, prefix="/api/v1")
app.include_router(shares.public_router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "db": settings.DB_NAME}