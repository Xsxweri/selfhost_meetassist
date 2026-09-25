import uuid

from app.curd.memory import create_memory, supersede_memory
from app.services.llm_service import LlmService
from app.services.memory_service import MemoryService

_V1 = [1.0] + [0.0] * 1023
_V2 = [0.0] * 1023 + [1.0]


def _patch_embed(monkeypatch, vec):
    async def fake_embed(self, text):
        return vec
    monkeypatch.setattr(LlmService, "_get_embedding", fake_embed)


async def test_recall_ranks_relevant_top(db_session, make_auth, monkeypatch):
    oid = uuid.UUID((await make_auth())["user_id"])
    await create_memory(db_session, owner_id=oid, content="批准预算500万", subject="预算", kind="decision", embedding=_V1)
    await create_memory(db_session, owner_id=oid, content="团建定在周五", subject="团建", embedding=_V2)
    _patch_embed(monkeypatch, _V1)
    hits = await MemoryService(db_session).recall("预算", oid)
    assert hits and hits[0]["content"] == "批准预算500万"


async def test_recall_keyword_path_rescues(db_session, make_auth, monkeypatch):
    oid = uuid.UUID((await make_auth())["user_id"])
    await create_memory(db_session, owner_id=oid, content="张三电话13800000000", subject="张三", embedding=_V2)
    _patch_embed(monkeypatch, _V1)   # 向量正交→低于 min_sim 被过滤，仅靠关键词命中
    hits = await MemoryService(db_session).recall("13800000000", oid)
    assert any("13800000000" in h["content"] for h in hits)


async def test_recall_owner_isolation(db_session, make_auth, monkeypatch):
    a = await make_auth(); b = await make_auth()
    await create_memory(db_session, owner_id=uuid.UUID(a["user_id"]), content="A的预算", subject="预算", embedding=_V1)
    _patch_embed(monkeypatch, _V1)
    hits = await MemoryService(db_session).recall("预算", uuid.UUID(b["user_id"]))
    assert hits == []


async def test_recall_excludes_superseded(db_session, make_auth, monkeypatch):
    oid = uuid.UUID((await make_auth())["user_id"])
    old = await create_memory(db_session, owner_id=oid, content="预算300万", subject="预算", embedding=_V1)
    new = await create_memory(db_session, owner_id=oid, content="预算500万", subject="预算", embedding=_V1)
    await supersede_memory(db_session, old, new.id)
    _patch_embed(monkeypatch, _V1)
    hits = await MemoryService(db_session).recall("预算", oid)
    assert all(h["id"] != old.id for h in hits)
    assert any(h["content"] == "预算500万" for h in hits)