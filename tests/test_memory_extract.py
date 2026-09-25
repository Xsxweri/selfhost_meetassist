import uuid

from app.curd.memory import list_memories
from app.models.meeting import Meeting
from app.services.llm_service import LlmService
from app.services.memory_service import MemoryService

_V1 = [1.0] + [0.0] * 1023
_V2 = [0.0] * 1023 + [1.0]


async def _set_summary(db_session, mid, text):
    m = await db_session.get(Meeting, uuid.UUID(mid))
    m.summary = text
    await db_session.commit()


async def test_ingest_creates_memories(db_session, make_auth, seed_meeting, monkeypatch):
    u = await make_auth()
    oid = uuid.UUID(u["user_id"])
    mid = await seed_meeting(u["headers"])
    await _set_summary(db_session, mid, "本次批准预算500万，张三负责Q3上线。")

    async def fake_extract(self, text):
        return [
            {"kind": "decision", "subject": "预算", "content": "批准预算500万", "importance": 0.9},
            {"kind": "action", "subject": "Q3上线", "content": "张三负责Q3上线", "importance": 0.7},
        ]
    monkeypatch.setattr(LlmService, "extract_memories", fake_extract)

    vecs = {"批准预算500万": _V1, "张三负责Q3上线": _V2}
    async def fake_embed(self, text):
        return vecs.get(text, [0.5] * 1024)
    monkeypatch.setattr(LlmService, "_get_embedding", fake_embed)

    res = await MemoryService(db_session).ingest_from_meeting(uuid.UUID(mid))
    assert res["ok"] and res["created"] == 2 and res["superseded"] == 0

    mems = await list_memories(db_session, oid)
    assert len(mems) == 2
    assert {m.kind for m in mems} == {"decision", "action"}


async def test_ingest_supersedes_on_reextract(db_session, make_auth, seed_meeting, monkeypatch):
    u = await make_auth()
    oid = uuid.UUID(u["user_id"])
    mid = await seed_meeting(u["headers"])
    await _set_summary(db_session, mid, "预算讨论")

    calls = {"n": 0}
    async def fake_extract(self, text):
        calls["n"] += 1
        content = "批准预算300万" if calls["n"] == 1 else "批准预算500万"
        return [{"kind": "decision", "subject": "预算", "content": content, "importance": 0.9}]
    monkeypatch.setattr(LlmService, "extract_memories", fake_extract)

    async def fake_embed(self, text):
        return _V1        # 两次同向量同 subject → 高相似 → 演进
    monkeypatch.setattr(LlmService, "_get_embedding", fake_embed)

    svc = MemoryService(db_session)
    r1 = await svc.ingest_from_meeting(uuid.UUID(mid))
    r2 = await svc.ingest_from_meeting(uuid.UUID(mid))
    assert r1["created"] == 1 and r1["superseded"] == 0
    assert r2["created"] == 1 and r2["superseded"] == 1

    current = await list_memories(db_session, oid)   # 默认排除被取代的
    assert len(current) == 1 and current[0].content == "批准预算500万"