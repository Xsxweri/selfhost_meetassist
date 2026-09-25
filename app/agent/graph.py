import json
import logging
import re
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agent.context import AgentContext
from app.agent.llm import chat
from app.agent.prompts import (
    build_plan_prompt,
    build_report_prompt,
    plan_system,
    report_system,
)
from app.agent.state import AgentState
from app.agent.tools import SENSITIVE_TOOLS, TOOLS, dispatch, tool_catalog
from app.core.config import get_settings
from app.curd.audit_log import record_event
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditAction
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)
settings = get_settings()

_CODE_FENCE = "`" * 3
_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)
_MAX_STEPS = 6
_SLIM_STR = 1000   # 单字段截断阈值（待办/纪要远小于此，仅防长转录）
_SLIM_LIST = 20          # 列表长度上限
_SLIM_TOTAL = 8000   # 单次导出内容总长度上限
_LARGE_KEYS = {"content_base64"}  # 直接剔除、仅保留占位大的字段


# ==================== 节点 ====================
async def recall(state: AgentState) -> dict:
    """RAG 注入：检索与目标相关的长期记忆供 planner 参考；失败静默降级为空记忆"""
    if not settings.MEMORY_ENABLED:
        return {}
    goal = (state.get("goal") or "").strip()
    if not goal:
        return {}
    try:
        async with AsyncSessionLocal() as db:
            hits = await MemoryService(db).recall(
                goal, uuid.UUID(state["owner_id"]), limit=settings.MEMORY_TOP_K
            )
        return {"memory_context": [
            {"kind": h.get("kind"), "subject": h.get("subject"), "content": h.get("content")}
            for h in hits
        ]}
    except Exception as e:  # noqa: BLE001 - 记忆检索失败不阻断主流程
        logger.warning("memory recall failed, degrade to no-memory: %s", e)
        return {}


async def planner(state: AgentState) -> dict:
    prompt = build_plan_prompt(tool_catalog(), state.get("history") or [], state["goal"], state.get("memory_context") or [])
    raw = await chat(prompt, system=plan_system(), json_mode=True)
    plan = _parse_plan(raw)
    return {"plan": plan, "cursor": 0, "results": []}


def _parse_plan(raw: str) -> list[dict]:
    cleaned = (raw or "").strip()
    if cleaned.startswith(_CODE_FENCE):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    data = None
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        m = _JSON_OBJ.search(cleaned)
        if m:
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                data = None
    if not isinstance(data, dict):
        logger.warning("planner 输出无法解析为 JSON，回退空计划。raw=%r", (raw or "")[:200])
        return []
    steps = data.get("steps")
    if not isinstance(steps, list):
        return []
    valid = []
    for s in steps[:_MAX_STEPS]:
        if not isinstance(s, dict):
            continue
        name = s.get("tool")
        if name not in TOOLS:
            continue
        args = s.get("args") if isinstance(s.get("args"), dict) else {}
        valid.append({"tool": name, "args": args, "reason": s.get("reason", "")})
    return valid


def _slim_result(obj, _depth: int = 0):
    """裁剪工具结果，防止导出内容/base64/长转录撑爆 reporter 的 LLM 上下文"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _LARGE_KEYS:
                out[k] = f"<omitted {len(str(v))} chars>"
            else:
                out[k] = _slim_result(v, _depth + 1)
        return out
    if isinstance(obj, list):
        return [_slim_result(x, _depth + 1) for x in obj[:_SLIM_LIST]]
    if isinstance(obj, str) and len(obj) > _SLIM_STR:
        return obj[:_SLIM_STR] + f"...(+{len(obj) - _SLIM_STR})"
    return obj


def _enforce_budget(result: dict) -> dict:
    """二级防线：list×field 乘积仍可能超预算，对序列化总量做硬截断"""
    text = json.dumps(result, ensure_ascii=False)
    if len(text) <= _SLIM_TOTAL:
        return result
    return {
        "ok": result.get("ok"),
        "budget_truncated": True,
        "note": f"结果过大已截断（原 {len(text)} 字符）",
        "preview": text[:_SLIM_TOTAL],
    }


def router(state: AgentState) -> dict:
    """纯路由节点，不做业务"""
    return {}


def route_fn(state: AgentState) -> str:
    plan = state.get("plan") or []
    cursor = state.get("cursor", 0)
    if cursor >= len(plan):
        return "reporter"
    spec = TOOLS.get(plan[cursor]["tool"])
    if spec and spec.sensitive:
        return "human_gate"
    return "executor"


def human_gate(state: AgentState) -> dict:
    """敏感操作人工确认闸门：interrupt 暂停，等待 /agent/resume"""
    step = (state.get("plan") or [])[state.get("cursor", 0)]
    decision = interrupt({
        "type": "confirm",
        "tool": step["tool"],
        "args": step.get("args", {}),
        "reason": step.get("reason", ""),
        "message": f"Agent 请求执行敏感操作：{step['tool']}，是否批准？",
    })
    approved = bool((decision or {}).get("approved"))
    if approved:
        return {"gate_decision": "approve"}
    skipped = {"tool": step["tool"], "args": step.get("args", {}),
               "result": {"ok": False, "skipped": True, "error": "user denied"}}
    return {
        "gate_decision": "deny",
        "cursor": state.get("cursor", 0) + 1,
        "results": (state.get("results") or []) + [skipped],
    }


def gate_fn(state: AgentState) -> str:
    return "executor" if state.get("gate_decision") == "approve" else "router"


async def executor(state: AgentState) -> dict:
    step = (state.get("plan") or [])[state.get("cursor", 0)]
    name, args = step["tool"], step.get("args", {})
    async with AsyncSessionLocal() as db:
        ctx = AgentContext(
            db=db,
            owner_id=uuid.UUID(state["owner_id"]),
            user_id=uuid.UUID(state["user_id"]),
            ip=state.get("ip"),
            user_agent=state.get("user_agent"),
        )
        result = await dispatch(ctx, name, args)
        # 敏感操作成功 → 单独留痕
        if name in SENSITIVE_TOOLS and result.get("ok"):
            await record_event(
                db,
                action=AuditAction.AGENT_ACTION.value,
                user_id=ctx.user_id,
                resource="agent",
                detail={"tool": name, "args": _safe_args(args)},
                ip_address=ctx.ip,
                user_agent=ctx.user_agent,
            )
    return {
        "cursor": state.get("cursor", 0) + 1,
        "results": (state.get("results") or []) + [
            {"tool": name, "args": args, "result": _enforce_budget(_slim_result(result))}
        ],
    }


def _safe_args(args: dict) -> dict:
    """审计留痕时截断超长字段（如导出内容）"""
    out = {}
    for k, v in (args or {}).items():
        sv = str(v)
        out[k] = sv if len(sv) <= 200 else sv[:200] + "...(truncated)"
    return out


async def reporter(state: AgentState) -> dict:
    prompt = build_report_prompt(state["goal"], state.get("results") or [])
    text = await chat(prompt, system=report_system())
    return {"final_report": text.strip(), "status": "done"}


async def audit(state: AgentState) -> dict:
    async with AsyncSessionLocal() as db:
        await record_event(
            db,
            action=AuditAction.AGENT_RUN.value,
            user_id=uuid.UUID(state["user_id"]),
            resource="agent",
            detail={
                "goal": state["goal"],
                "status": state.get("status"),
                "steps": [
                    {"tool": r.get("tool"), "ok": (r.get("result") or {}).get("ok"),
                     "skipped": (r.get("result") or {}).get("skipped", False)}
                    for r in (state.get("results") or [])
                ],
            },
            ip_address=state.get("ip"),
            user_agent=state.get("user_agent"),
        )
    return {}


# ==================== 组图 ====================
def build_graph(checkpointer=None):
    b = StateGraph(AgentState)
    b.add_node("recall", recall)
    b.add_node("planner", planner)
    b.add_node("router", router)
    b.add_node("human_gate", human_gate)
    b.add_node("executor", executor)
    b.add_node("reporter", reporter)
    b.add_node("audit", audit)

    b.add_edge(START, "recall")
    b.add_edge("recall", "planner")
    b.add_edge("planner", "router")
    b.add_conditional_edges("router", route_fn,
                            {"human_gate": "human_gate", "executor": "executor", "reporter": "reporter"})
    b.add_conditional_edges("human_gate", gate_fn, {"executor": "executor", "router": "router"})
    b.add_edge("executor", "router")
    b.add_edge("reporter", "audit")
    b.add_edge("audit", END)

    # 注意：InMemorySaver 仅单进程有效；多进程/持久化需改用
    # langgraph-checkpoint-postgres（需在 pyproject 增加依赖）
    return b.compile(checkpointer=checkpointer or InMemorySaver())