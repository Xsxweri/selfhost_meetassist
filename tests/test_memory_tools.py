import uuid

from app.agent import tools
from app.agent.context import AgentContext
from app.services.llm_service import LlmService

_V1 = [1.0] + [0.0] * 1023


def _patch_embed(monkeypatch, vec=_V1):
    async def fake_embed(self, text):
        return vec
    monkeypatch.setattr(LlmService, "_get_embedding", fake_embed)


def _ctx(db, oid):
    return AgentContext(db=db, owner_id=oid, user_id=oid, ip=None, user_agent=None)


async def test_remember_then_recall_roundtrip(db_session, make_auth, monkeypatch):
    _patch_embed(monkeypatch)
    oid = uuid.UUID((await make_auth())["user_id"])
    ctx = _ctx(db_session, oid)
    w = await tools._remember(ctx, {"content": "批准预算500万", "kind": "decision", "subject": "预算"})
    assert w["ok"] and w["kind"] == "decision"
    r = await tools._recall(ctx, {"query": "预算"})
    assert r["ok"] and any("批准预算500万" in m["content"] for m in r["memories"])


async def test_remember_invalid_kind_defaults_fact(db_session, make_auth, monkeypatch):
    _patch_embed(monkeypatch)
    oid = uuid.UUID((await make_auth())["user_id"])
    w = await tools._remember(_ctx(db_session, oid), {"content": "随便记一条", "kind": "bogus"})
    assert w["ok"] and w["kind"] == "fact"


async def test_remember_empty_content_errors(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    w = await tools._remember(_ctx(db_session, oid), {"content": "  "})
    assert w == {"ok": False, "error": "content required"}


async def test_recall_owner_isolation_via_tool(db_session, make_auth, monkeypatch):
    _patch_embed(monkeypatch)
    a = uuid.UUID((await make_auth())["user_id"])
    b = uuid.UUID((await make_auth())["user_id"])
    await tools._remember(_ctx(db_session, a), {"content": "A的预算500万", "subject": "预算"})
    r = await tools._recall(_ctx(db_session, b), {"query": "预算"})
    assert r["ok"] and r["memories"] == []


async def test_recall_requires_query(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    r = await tools._recall(_ctx(db_session, oid), {"query": ""})
    assert r == {"ok": False, "error": "query required"}