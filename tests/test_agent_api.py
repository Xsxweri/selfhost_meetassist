"""Agent API 测试(端到端 + 真实越权拦截)"""

import json

import app.agent.graph as agent_graph


def _plan_chat(monkeypatch, plan_steps, report_text="已完成。", capture=None):
    """把 planner/reporter 的 LLM 调用替换为确定输出"""
    async def fake_chat(prompt, system=None, json_mode=False):
        if json_mode:
            return json.dumps({"steps": plan_steps})
        if capture is not None:
            capture["report_prompt"] = prompt
        return report_text
    monkeypatch.setattr(agent_graph, "chat", fake_chat)


async def test_chat_readonly_list_meetings(client, make_auth, seed_meeting, monkeypatch):
    u = await make_auth()
    await seed_meeting(u["headers"])
    _plan_chat(monkeypatch, [{"tool": "list_meetings", "args": {"limit": 10}, "reason": "r"}])
    r = await client.post("/api/v1/agent/chat", headers=u["headers"], json={"message": "列出我的会议"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "done"
    assert body["thread_id"] and body["report"]


async def test_chat_export_gate_then_resume_approve(client, make_auth, seed_meeting, monkeypatch):
    u = await make_auth()
    mid = await seed_meeting(u["headers"])
    _plan_chat(monkeypatch, [{"tool": "export_meeting", "args": {"meeting_id": mid, "format": "md"}, "reason": "r"}])

    r = await client.post("/api/v1/agent/chat", headers=u["headers"], json={"message": "导出这个会议"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "awaiting_confirmation"
    assert body["confirmation"]["tool"] == "export_meeting"

    r2 = await client.post("/api/v1/agent/resume", headers=u["headers"],
                           json={"thread_id": body["thread_id"], "approved": True})
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "done"


async def test_resume_cross_user_forbidden(client, make_auth, seed_meeting, monkeypatch):
    a = await make_auth()
    b = await make_auth()
    mid = await seed_meeting(a["headers"])
    _plan_chat(monkeypatch, [{"tool": "export_meeting", "args": {"meeting_id": mid, "format": "md"}, "reason": "r"}])

    r = await client.post("/api/v1/agent/chat", headers=a["headers"], json={"message": "导出"})
    assert r.json()["status"] == "awaiting_confirmation"
    tid = r.json()["thread_id"]

    # B 拿到 A 的 thread_id 也无法批准
    r2 = await client.post("/api/v1/agent/resume", headers=b["headers"],
                           json={"thread_id": tid, "approved": True})
    assert r2.status_code == 403


async def test_resume_unknown_thread_rejected(client, make_auth):
    u = await make_auth()
    r = await client.post("/api/v1/agent/resume", headers=u["headers"],
                          json={"thread_id": "nope-unknown", "approved": True})
    assert r.status_code == 403     # 磁盘实现：未知 thread 返回 403


async def test_tool_blocks_cross_user_meeting(client, make_auth, seed_meeting, monkeypatch):
    a = await make_auth()
    b = await make_auth()
    mid = await seed_meeting(a["headers"])
    capture = {}
    _plan_chat(monkeypatch, [{"tool": "get_meeting_detail", "args": {"meeting_id": mid}, "reason": "r"}],
               capture=capture)

    r = await client.post("/api/v1/agent/chat", headers=b["headers"], json={"message": "看这个会议"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "done"
    # 工具层 _owned 拦截跨用户访问：reporter 收到的结果里含 not owned/not found
    assert "not owned" in capture["report_prompt"] or "not found" in capture["report_prompt"]