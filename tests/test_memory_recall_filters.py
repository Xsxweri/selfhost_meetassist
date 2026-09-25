import uuid

from app.curd.memory import create_memory, soft_delete_memory
from app.services import memory_service
from app.services.llm_service import LlmService
from app.services.memory_service import MemoryService

_V1 = [1.0] + [0.0] * 1023
_V2 = [0.0] * 1023 + [1.0]


def _patch_embed(monkeypatch, vec):
    async def fake_embed(self, text):
        return vec
    monkeypatch.setattr(LlmService, "_get_embedding", fake_embed)


async def test_recall_kind_filter(db_session, make_auth, monkeypatch):
    oid = uuid.UUID((await make_auth())["user_id"])
    await create_memory(db_session, owner_id=oid, content="批准预算500万", subject="预算", kind="decision", embedding=_V1)
    await create_memory(db_session, owner_id=oid, content="预算相关的闲聊", subject="预算", kind="fact", embedding=_V1)
    _patch_embed(monkeypatch, _V1)
    hits = await MemoryService(db_session).recall("预算", oid, kind="decision")
    assert hits and all(h["kind"] == "decision" for h in hits)


async def test_recall_subject_filter(db_session, make_auth, monkeypatch):
    oid = uuid.UUID((await make_auth())["user_id"])
    await create_memory(db_session, owner_id=oid, content="预算500万", subject="预算", embedding=_V1)
    await create_memory(db_session, owner_id=oid, content="团建周五", subject="团建", embedding=_V1)
    _patch_embed(monkeypatch, _V1)
    hits = await MemoryService(db_session).recall("x", oid, subject="团建")
    assert hits and all(h["subject"] == "团建" for h in hits)


async def test_recall_limit_cap(db_session, make_auth, monkeypatch):
    oid = uuid.UUID((await make_auth())["user_id"])
    for i in range(5):
        await create_memory(db_session, owner_id=oid, content=f"预算条目{i}", subject="预算", embedding=_V1)
    _patch_embed(monkeypatch, _V1)
    hits = await MemoryService(db_session).recall("预算", oid, limit=2)
    assert len(hits) <= 2


async def test_recall_empty_query(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    assert await MemoryService(db_session).recall("   ", oid) == []


async def test_recall_excludes_soft_deleted(db_session, make_auth, monkeypatch):
    oid = uuid.UUID((await make_auth())["user_id"])
    m = await create_memory(db_session, owner_id=oid, content="批准预算500万", subject="预算", embedding=_V1)
    await soft_delete_memory(db_session, m)
    _patch_embed(monkeypatch, _V1)
    hits = await MemoryService(db_session).recall("预算", oid)
    assert all(h["id"] != m.id for h in hits)


async def test_recall_hybrid_off_drops_keyword_only(db_session, make_auth, monkeypatch):
    """关闭混合检索后，仅靠关键词命中的记忆应消失（向量正交被 min_sim 过滤）"""
    oid = uuid.UUID((await make_auth())["user_id"])
    await create_memory(db_session, owner_id=oid, content="张三电话13800000000", subject="张三", embedding=_V2)
    _patch_embed(monkeypatch, _V1)
    svc = MemoryService(db_session)
    assert any("13800000000" in h["content"] for h in await svc.recall("13800000000", oid))
    monkeypatch.setattr(memory_service.settings, "MEMORY_HYBRID", False)
    assert await svc.recall("13800000000", oid) == []


async def test_recall_carries_meeting_id(db_session, make_auth, seed_meeting, monkeypatch):
    """跨会议溯源：召回结果应携带来源 meeting_id"""
    _patch_embed(monkeypatch, _V1)
    auth = await make_auth()
    oid = uuid.UUID(auth["user_id"])
    mid = await seed_meeting(auth["headers"])
    await create_memory(db_session, owner_id=oid, content="批准预算500万", subject="预算",
                        kind="decision", embedding=_V1, meeting_id=uuid.UUID(mid))
    hits = await MemoryService(db_session).recall("预算", oid)
    assert hits and str(hits[0]["meeting_id"]) == mid