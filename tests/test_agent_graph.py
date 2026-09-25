import uuid

import pytest
from langgraph.types import Command

import app.agent.graph as g

OWNER = str(uuid.uuid4())


def _input(goal: str) -> dict:
    return {
        "owner_id": OWNER, "user_id": OWNER, "ip": None, "user_agent": None,
        "goal": goal, "history": [{"role": "user", "content": goal}],
    }


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


@pytest.fixture
def patched(monkeypatch):
    """隔离 DB / LLM / 审计，仅测状态机逻辑"""
    monkeypatch.setattr(g, "AsyncSessionLocal", lambda: _FakeSession())

    class _FakeMemoryService:
        def __init__(self, db): pass

        async def recall(self, *a, **k): return []

    monkeypatch.setattr(g, "MemoryService", _FakeMemoryService)

    async def _no_record(*a, **k):
        return None
    monkeypatch.setattr(g, "record_event", _no_record)

    calls: list[tuple] = []

    async def _fake_dispatch(ctx, name, args):
        calls.append((name, args))
        return {"ok": True, "tool": name}
    monkeypatch.setattr(g, "dispatch", _fake_dispatch)

    def set_chat(plan_json: str, report: str = "完成"):
        async def _chat(prompt, system=None, json_mode=False):
            return plan_json if json_mode else report
        monkeypatch.setattr(g, "chat", _chat)

    return {"calls": calls, "set_chat": set_chat}


async def test_readonly_plan_executes(patched):
    patched["set_chat"]('{"steps":[{"tool":"list_meetings","args":{"limit":5},"reason":"r"}]}')
    graph = g.build_graph()
    res = await graph.ainvoke(_input("列出会议"), config={"configurable": {"thread_id": "t1"}})
    assert res["status"] == "done"
    assert "__interrupt__" not in res
    assert patched["calls"] == [("list_meetings", {"limit": 5})]
    assert res["final_report"] == "完成"


async def test_empty_plan_goes_straight_to_report(patched):
    patched["set_chat"]('{"steps":[]}')
    graph = g.build_graph()
    res = await graph.ainvoke(_input("你好"), config={"configurable": {"thread_id": "t2"}})
    assert res["status"] == "done"
    assert patched["calls"] == []


async def test_sensitive_interrupts_then_approve(patched):
    patched["set_chat"]('{"steps":[{"tool":"export_meeting","args":{"meeting_id":"m","format":"pdf"},"reason":"r"}]}')
    graph = g.build_graph()
    cfg = {"configurable": {"thread_id": "t3"}}

    res = await graph.ainvoke(_input("导出PDF"), config=cfg)
    assert "__interrupt__" in res
    assert res["__interrupt__"][0].value["tool"] == "export_meeting"
    assert patched["calls"] == []

    res2 = await graph.ainvoke(Command(resume={"approved": True}), config=cfg)
    assert res2["status"] == "done"
    assert patched["calls"] == [("export_meeting", {"meeting_id": "m", "format": "pdf"})]


async def test_sensitive_deny_skips_execution(patched):
    patched["set_chat"]('{"steps":[{"tool":"create_share_link","args":{"meeting_id":"m"},"reason":"r"}]}')
    graph = g.build_graph()
    cfg = {"configurable": {"thread_id": "t4"}}

    res = await graph.ainvoke(_input("分享"), config=cfg)
    assert "__interrupt__" in res

    res2 = await graph.ainvoke(Command(resume={"approved": False}), config=cfg)
    assert res2["status"] == "done"
    assert patched["calls"] == []
    assert any((r.get("result") or {}).get("skipped") for r in res2["results"])


async def test_mixed_plan_stops_at_first_sensitive(patched):
    patched["set_chat"]('{"steps":['
                        '{"tool":"list_meetings","args":{},"reason":"r1"},'
                        '{"tool":"update_action_item","args":{"meeting_id":"m","item_id":"i","status":"done"},"reason":"r2"}]}')
    graph = g.build_graph()
    cfg = {"configurable": {"thread_id": "t5"}}

    res = await graph.ainvoke(_input("标记待办完成"), config=cfg)
    assert "__interrupt__" in res
    assert patched["calls"] == [("list_meetings", {})]
    assert res["__interrupt__"][0].value["tool"] == "update_action_item"


async def test_recall_node_injects_memory(patched, monkeypatch):
    """recall 节点检索到的长期记忆应注入 planner 提示词（RAG）"""
    class _Mem:
        def __init__(self, db): pass
        async def recall(self, query, owner_id, **k):
            return [{"kind": "decision", "subject": "预算", "content": "批准预算500万"}]
    monkeypatch.setattr(g, "MemoryService", _Mem)

    seen = {}
    async def _chat(prompt, system=None, json_mode=False):
        if json_mode:
            seen["plan_prompt"] = prompt
            return '{"steps":[]}'
        return "完成"
    monkeypatch.setattr(g, "chat", _chat)

    graph = g.build_graph()
    res = await graph.ainvoke(_input("预算多少"), config={"configurable": {"thread_id": "t6"}})
    assert res["status"] == "done"
    assert res.get("memory_context")
    assert "批准预算500万" in seen["plan_prompt"]