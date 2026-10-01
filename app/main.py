import asyncio
from contextlib import asynccontextmanager
import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from app.api.v1 import meetings, auth, consents, stream, summaries, audit, shares, exports, tasks, search, agent, memory
from app.agent.checkpoint import make_checkpointer
from app.agent.graph import build_graph
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import AsyncSessionLocal


settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 表结构统一由 alembic 管理，启动不再自动 create_all
    checkpointer, cleanup = await make_checkpointer()
    app.state.graph = build_graph(checkpointer=checkpointer)
    app.state.checkpointer_type = type(checkpointer).__name__
    try:
        yield
    finally:
        if cleanup:
            await cleanup()

app = FastAPI(
    title=settings.APP_NAME,
    description="AI驱动的会议助理",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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
app.include_router(memory.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}


async def _check_db() -> str:
    async with AsyncSessionLocal() as s:
        await s.execute(text("SELECT 1"))
    return "ok"


async def _check_redis() -> str:
    r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3, socket_timeout=3)
    try:
        await r.ping()
        return "ok"
    finally:
        await r.aclose()


async def _check_ollama() -> str:
    async with httpx.AsyncClient(timeout=5.0) as c:
        resp = await c.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        resp.raise_for_status()
    return "ok"


@app.get("/health")
async def health_check():
    async def _run(fn):
        try:
            return await asyncio.wait_for(fn(), timeout=6.0)
        except Exception as e:  # noqa: BLE001
            return f"error: {type(e).__name__}"

    db, redis_st, ollama = await asyncio.gather(
        _run(_check_db), _run(_check_redis), _run(_check_ollama)
    )
    all_ok = db == "ok" and redis_st == "ok" and ollama == "ok"
    payload = {
        "status": "ok" if all_ok else "degraded",
        "db": db,
        "redis": redis_st,
        "ollama": ollama,
        "checkpoint": getattr(app.state, "checkpointer_type", settings.CHECKPOINT_BACKEND),
    }
    # 仅核心依赖 DB 不可用返回 503 供容器探针判断；redis/ollama 异常标记 degraded 但仍 200
    return JSONResponse(content=payload, status_code=200 if db == "ok" else 503)