import pytest

from app.agent.graph import (
    _MAX_STEPS, _SLIM_STR, _SLIM_TOTAL, _enforce_budget, _parse_plan, _safe_args, _slim_result,
)
from app.agent.tools import SENSITIVE_TOOLS, TOOLS, dispatch, tool_catalog
from app.core.prompts import load_prompt, render_prompt


# ==================== planner 解析 ====================
def test_parse_plan_valid():
    raw = '{"steps":[{"tool":"list_meetings","args":{"limit":5},"reason":"r"}]}'
    assert _parse_plan(raw) == [{"tool": "list_meetings", "args": {"limit": 5}, "reason": "r"}]


def test_parse_plan_code_fence():
    raw = '```json\n{"steps":[{"tool":"recall","args":{"query":"x"}}]}\n```'
    plan = _parse_plan(raw)
    assert len(plan) == 1
    assert plan[0]["tool"] == "recall"
    assert plan[0]["reason"] == ""


def test_parse_plan_recovers_json_from_noise():
    raw = '好的，规划如下：\n{"steps":[{"tool":"list_meetings","args":{}}]}\n以上。'
    plan = _parse_plan(raw)
    assert len(plan) == 1 and plan[0]["tool"] == "list_meetings"


def test_parse_plan_filters_unknown_tool():
    raw = '{"steps":[{"tool":"drop_database","args":{}},{"tool":"list_meetings","args":{}}]}'
    plan = _parse_plan(raw)
    assert len(plan) == 1 and plan[0]["tool"] == "list_meetings"


def test_parse_plan_caps_steps():
    steps = ",".join('{"tool":"list_meetings","args":{}}' for _ in range(_MAX_STEPS + 4))
    assert len(_parse_plan('{"steps":[' + steps + ']}')) == _MAX_STEPS


@pytest.mark.parametrize("bad", ["", "not json", '{"steps":"nope"}', '{"foo":1}'])
def test_parse_plan_invalid_returns_empty(bad):
    assert _parse_plan(bad) == []


# ==================== 工具目录 ====================
def test_exactly_eight_tools():
    assert len(TOOLS) == 8


def test_sensitive_tools_set():
    assert SENSITIVE_TOOLS == {"update_action_item", "create_share_link", "export_meeting"}


def test_catalog_lists_every_tool_and_sensitive_flag():
    catalog = tool_catalog()
    for name in TOOLS:
        assert name in catalog
    assert "【敏感·需确认】" in catalog


async def test_dispatch_unknown_tool_returns_error():
    result = await dispatch(None, "nope", {})
    assert result == {"ok": False, "error": "unknown tool: nope"}


# ==================== 结果裁剪 ====================
def test_slim_result_drops_large_and_truncates():
    long_str = "s" * (_SLIM_STR + 400)
    big = {"ok": True, "content_base64": "A" * 5000, "summary": long_str,
           "items": [{"i": n} for n in range(50)]}
    out = _slim_result(big)
    assert "omitted" in out["content_base64"]
    assert len(out["summary"]) < len(long_str)      # 超阈值被截断
    assert out["summary"].endswith(f"...(+{len(long_str) - _SLIM_STR})")
    assert len(out["items"]) == 20


def test_enforce_budget_caps_total_size():
    """二级防线：list×field 乘积超预算时整体硬截断"""
    huge = {"ok": True, "items": [{"text": "y" * (_SLIM_STR - 1)} for _ in range(20)]}
    out = _enforce_budget(_slim_result(huge))
    assert out.get("budget_truncated") is True
    assert len(out["preview"]) <= _SLIM_TOTAL


def test_slim_result_preserves_action_item_content():
    """回归：待办正文字段名恰为 content，绝不能被 _LARGE_KEYS 抹掉"""
    result = {
        "ok": True,
        "action_items": [
            {"id": "x", "content": "写周报并发给张总", "assignee": "我", "status": "pending"},
        ],
    }
    out = _slim_result(result)
    assert out["action_items"][0]["content"] == "写周报并发给张总"

# ==================== 审计脱敏 ====================
def test_safe_args_truncates_long_values():
    out = _safe_args({"content": "x" * 300, "format": "pdf"})
    assert out["format"] == "pdf"
    assert out["content"].endswith("...(truncated)")
    assert len(out["content"]) < 250


# ==================== 提示词文件 ====================
@pytest.mark.parametrize("name", [
    "agent_plan_system", "agent_plan_user",
    "agent_report_system", "agent_report_user", "summary_user",
])
def test_prompt_files_exist_and_nonempty(name):
    assert load_prompt(name).strip()


def test_prompt_placeholders_present():
    plan_user = load_prompt("agent_plan_user")
    assert "{{catalog}}" in plan_user and "{{goal}}" in plan_user and "{{history}}" in plan_user
    assert "{{memory}}" in plan_user
    assert "{{transcript}}" in load_prompt("summary_user")
    assert "{{goal}}" in load_prompt("agent_report_user")


def test_render_replaces_placeholders():
    out = render_prompt("summary_user", transcript="ABC")
    assert "{{transcript}}" not in out and "ABC" in out


def test_missing_prompt_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist")