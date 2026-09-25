"""NullPool 隔离 + Agent 会话补丁"""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  确保所有模型注册到 Base.metadata
import app.agent.graph as agent_graph
from app.api import deps
from app.core.config import get_settings
from app.db.session import Base
from app.main import app

settings = get_settings()

TEST_DB_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/meeting_assistant_test"
)

# NullPool：每次取新连接用完即弃，规避 session 级建表与 function 级测试的事件循环绑定冲突
test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

_TRUNCATE = (
    "TRUNCATE TABLE users, meetings, transcripts, action_items, "
    "consents, share_links, audit_logs, memories, conversation_threads CASCADE"
)


@pytest_asyncio.fixture
async def db_session(_setup_schema):
    """直接操作测试库的会话（curd 层单元测试用）"""
    async with TestSessionLocal() as session:
        yield session


async def _override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def _setup_schema():
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(_setup_schema):
    yield
    async with TestSessionLocal() as session:
        await session.execute(text(_TRUNCATE))
        await session.commit()


@pytest_asyncio.fixture
async def client(_setup_schema, monkeypatch):
    app.dependency_overrides[deps.get_db] = _override_get_db
    # 关键：Agent 图 executor/audit 绕过 DI 直接引用 AsyncSessionLocal，必须一并指向测试库
    monkeypatch.setattr(agent_graph, "AsyncSessionLocal", TestSessionLocal)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def make_auth(client):
    """注册+登录，返回 {headers, user_id}"""
    async def _make(password: str = "testpass123"):
        email = f"u_{uuid.uuid4().hex[:10]}@test.com"
        r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        r = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200, me.text
        return {"headers": headers, "user_id": me.json()["id"]}
    return _make


@pytest_asyncio.fixture
async def seed_meeting(client):
    """用指定用户建一场会议，返回 meeting_id"""
    async def _seed(headers, title="预算评审会"):
        r = await client.post("/api/v1/meetings", headers=headers, json={"title": title})
        assert r.status_code == 201, r.text
        return r.json()["id"]
    return _seed