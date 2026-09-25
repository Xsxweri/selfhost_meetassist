import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from sqlalchemy import select

from app.agent.context import AgentContext
from app.curd.action_item import (
    get_action_item,
    list_action_items,
    replace_action_items,
    update_action_item,
)
from app.curd.meeting import get_meeting, list_meetings
from app.curd.memory import create_memory
from app.curd.audit_log import record_event
from app.curd.share_link import create_share_link
from app.models.audit_log import AuditAction
from app.models.memory import MemoryKind
from app.models.transcript import Transcript
from app.services import export_service
from app.services.llm_service import LlmService
from app.services.memory_service import MemoryService

_NULLISH = {"", "null", "none", "无", "n/a"}
_VALID_KINDS = {k.value for k in MemoryKind}


def _clamp_importance(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))


@dataclass
class ToolSpec:
    name: str
    description: str
    params: dict[str, Any]   # JSON Schema {参数名: {type, required, desc, default}}
    sensitive: bool          # True = 需人工确认闸门
    handler: Callable[[AgentContext, dict], Awaitable[dict]]


def _parse_due(value: Any) -> datetime | None:
    """解析 due_date"""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if v.lower() in _NULLISH:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def _item_dict(a) -> dict:
    """将 ActionItem 转换为字典"""
    return {
        "id": str(a.id),
        "content": a.content,
        "assignee": a.assignee,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "priority": a.priority,
        "status": a.status,
    }


async def _owned(ctx: AgentContext, meeting_id: Any):
    """校验会议归属，返回 Meeting 或错误 dict"""
    try:
        mid = uuid.UUID(str(meeting_id))
    except (ValueError, TypeError):
        return {"ok": False, "error": "invalid meeting_id"}
    m = await get_meeting(ctx.db, mid, owner_id=ctx.owner_id)
    if not m:
        return {"ok": False, "error": "meeting not found or not owned"}
    return m


# ==================== 统一召回（记忆 + 证据） ====================
async def _recall(ctx: AgentContext, args: dict) -> dict:
    query = (args.get("query") or "").strip()
    if not query:
        return {"ok": False, "error": "query required"}
    limit = min(int(args.get("limit") or 6), 20)
    kind = args.get("kind") or None
    subject = args.get("subject") or None
    memories = await MemoryService(ctx.db).recall(
        query, ctx.owner_id, kind=kind, subject=subject, limit=limit
    )
    mem_out = [
        {
            "kind": m.get("kind"), "subject": m.get("subject"), "content": m.get("content"),
            "meeting_id": str(m["meeting_id"]) if m.get("meeting_id") else None,
            "score": m.get("score"),
        }
        for m in memories
    ]
    evidence = []
    if args.get("include_evidence"):
        rows = await LlmService(ctx.db).semantic_search(
            query, owner_id=str(ctx.owner_id), limit=limit
        )
        evidence = [
            {"meeting_id": str(r["meeting_id"]), "text": r["text"],
             "similarity": round(float(r["similarity"]), 3)}
            for r in rows
        ]
    return {"ok": True, "count": len(mem_out), "memories": mem_out, "evidence": evidence}


# ==================== 读写工具 ====================
async def _list_meetings(ctx: AgentContext, args: dict) -> dict:
    limit = min(int(args.get("limit") or 20), 50)
    ms = await list_meetings(ctx.db, ctx.owner_id, limit=limit)
    return {
        "ok": True,
        "count": len(ms),
        "meetings": [
            {
                "id": str(m.id),
                "title": m.title,
                "created_at": m.created_at.isoformat(),
                "has_summary": bool(m.summary),
            }
            for m in ms
        ],
    }


# ==================== 获取会议详情 ====================
async def _get_meeting_detail(ctx: AgentContext, args: dict) -> dict:
    m = await _owned(ctx, args.get("meeting_id"))
    if isinstance(m, dict):
        return m
    items = await list_action_items(ctx.db, m.id)
    return {
        "ok": True,
        "meeting": {
            "id": str(m.id),
            "title": m.title,
            "summary": m.summary,
            "created_at": m.created_at.isoformat(),
            "action_items": [_item_dict(i) for i in items],
        },
    }


# # ==================== 列出待办事项 ====================
# async def _list_action_items(ctx: AgentContext, args: dict) -> dict:
#     m = await _owned(ctx, args.get("meeting_id"))
#     if isinstance(m, dict):
#         return m
#     items = await list_action_items(ctx.db, m.id)
#     return {"ok": True, "count": len(items), "action_items": [_item_dict(i) for i in items]}


# ==================== 生成会议摘要 ====================
async def _generate_summary(ctx: AgentContext, args: dict) -> dict:
    m = await _owned(ctx, args.get("meeting_id"))
    if isinstance(m, dict):
        return m
    overwrite = bool(args.get("overwrite", False))
    if m.summary and not overwrite:
        items = await list_action_items(ctx.db, m.id)
        return {
            "ok": True, "skipped": True,
            "reason": "已存在纪要，未覆盖；如需重生成请传 overwrite=true",
            "summary": m.summary, "action_items": [_item_dict(i) for i in items],
        }
    data = await LlmService(ctx.db).generate_summary(str(m.id))
    summary_text = (data.get("summary") or "").strip()
    kps = data.get("key_points") or []
    if kps:
        summary_text = (summary_text + "\n\n要点：\n" + "\n".join(f"- {k}" for k in kps)).strip()
    m.summary = summary_text
    items = await replace_action_items(ctx.db, m.id, data.get("action_items", []))
    return {"ok": True, "summary": summary_text, "action_items": [_item_dict(i) for i in items]}


# ==================== 敏感工具（需人工确认） ====================
async def _update_action_item(ctx: AgentContext, args: dict) -> dict:
    m = await _owned(ctx, args.get("meeting_id"))
    if isinstance(m, dict):
        return m
    try:
        iid = uuid.UUID(str(args.get("item_id")))
    except (ValueError, TypeError):
        return {"ok": False, "error": "invalid item_id"}
    item = await get_action_item(ctx.db, m.id, iid)
    if not item:
        return {"ok": False, "error": "action item not found"}
    patch: dict[str, Any] = {}
    for f in ("content", "assignee", "priority", "status"):
        if args.get(f) is not None:
            patch[f] = args[f]
    if args.get("due_date"):
        patch["due_date"] = _parse_due(args["due_date"])
    if not patch:
        return {"ok": False, "error": "no fields to update"}
    item = await update_action_item(ctx.db, item, patch)
    return {"ok": True, "action_item": _item_dict(item)}


# ==================== 创建共享链接 ====================
async def _create_share_link(ctx: AgentContext, args: dict) -> dict:
    m = await _owned(ctx, args.get("meeting_id"))
    if isinstance(m, dict):
        return m
    exp = args.get("expires_in_days")
    link = await create_share_link(
        ctx.db,
        meeting_id=m.id,
        created_by=ctx.user_id,
        allow_download=bool(args.get("allow_download", True)),
        expires_in_days=int(exp) if exp else None,
    )
    return {
        "ok": True,
        "token": link.token,
        "allow_download": link.allow_download,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        "url": f"/api/v1/shared/{link.token}",
    }


# ==================== 导出会议 ====================
async def _export_meeting(ctx: AgentContext, args: dict) -> dict:
    m = await _owned(ctx, args.get("meeting_id"))
    if isinstance(m, dict):
        return m
    fmt = (args.get("format") or "md").lower()
    if fmt not in ("md", "json", "docx", "pdf"):
        return {"ok": False, "error": f"unsupported format: {fmt}"}
    items = await list_action_items(ctx.db, m.id)
    res = await ctx.db.execute(
        select(Transcript).where(Transcript.meeting_id == m.id).order_by(Transcript.created_at)
    )
    transcripts = list(res.scalars().all())
    content, _media, ext = export_service.build(fmt, m, items, transcripts)
    return {
        "ok": True,
        "format": fmt,
        "filename": f"meeting_{m.id}{ext}",
        "bytes": len(content),
        "download_url": f"/api/v1/meetings/{m.id}/export?format={fmt}",
    }


# ==================== 写入长期记忆（用户显式要求记住） ====================
async def _remember(ctx: AgentContext, args: dict) -> dict:
    content = (args.get("content") or "").strip()
    if not content:
        return {"ok": False, "error": "content required"}
    kind = args.get("kind") if args.get("kind") in _VALID_KINDS else "fact"
    subject = args.get("subject") or None
    importance = _clamp_importance(args.get("importance"))
    emb = await LlmService(ctx.db)._get_embedding(content)
    mem = await create_memory(
        ctx.db, owner_id=ctx.owner_id, content=content, kind=kind,
        subject=subject, importance=importance, embedding=emb,
    )
    await record_event(
        ctx.db, action=AuditAction.MEMORY_WRITE.value, user_id=ctx.user_id,
        resource="memory",
        detail={"memory_id": str(mem.id), "kind": kind, "subject": subject, "source": "agent_explicit"},
    )
    return {"ok": True, "memory_id": str(mem.id), "kind": kind, "subject": subject}


# ==================== 工具注册表 ====================
TOOLS: dict[str, ToolSpec] = {}


def _reg(spec: ToolSpec) -> None:
    TOOLS[spec.name] = spec


_reg(ToolSpec(
    name="recall",
    description="跨会议统一召回：优先返回提炼后的长期记忆（决策/承诺/偏好/事实），可选下钻转录证据。用于“上次关于X的结论”这类问题",
    params={
        "query": {"type": "str", "required": True, "desc": "检索词/自然语言问题"},
        "kind": {"type": "str", "required": False, "desc": "decision|action|preference|fact|entity"},
        "subject": {"type": "str", "required": False, "desc": "主题/实体过滤"},
        "limit": {"type": "int", "required": False, "desc": "返回条数", "default": 6},
        "include_evidence": {"type": "bool", "required": False, "desc": "是否附带转录原文证据", "default": False},
    },
    sensitive=False, handler=_recall,
))
_reg(ToolSpec(
    name="list_meetings",
    description="列出当前用户最近的会议（标题/时间/是否有纪要）",
    params={"limit": {"type": "int", "required": False, "desc": "返回条数", "default": 20}},
    sensitive=False, handler=_list_meetings,
))
_reg(ToolSpec(
    name="get_meeting_detail",
    description="获取单场会议的标题、纪要与待办明细",
    params={"meeting_id": {"type": "str", "required": True, "desc": "会议UUID"}},
    sensitive=False, handler=_get_meeting_detail,
))
_reg(ToolSpec(
    name="generate_summary",
    description="为某场会议生成结构化纪要与待办并落库；若已有纪要默认不覆盖，需 overwrite=true 才重生成",
    params={
        "meeting_id": {"type": "str", "required": True, "desc": "会议UUID"},
        "overwrite": {"type": "bool", "required": False, "desc": "已有纪要时是否覆盖重生成", "default": False},
    },
    sensitive=False, handler=_generate_summary,
))
_reg(ToolSpec(
    name="remember",
    description="把用户明确要求记住的信息写入长期记忆（跨会议可召回）",
    params={
        "content": {"type": "str", "required": True, "desc": "要记住的一句话结论"},
        "kind": {"type": "str", "required": False, "desc": "decision|action|preference|fact|entity", "default": "fact"},
        "subject": {"type": "str", "required": False, "desc": "主题/实体关键词"},
        "importance": {"type": "float", "required": False, "desc": "0~1 重要度", "default": 0.5},
    },
    sensitive=False, handler=_remember,
))
_reg(ToolSpec(
    name="update_action_item",
    description="修改待办的内容/负责人/截止/优先级/状态（如标记 done、confirmed）",
    params={
        "meeting_id": {"type": "str", "required": True, "desc": "会议UUID"},
        "item_id": {"type": "str", "required": True, "desc": "待办UUID"},
        "content": {"type": "str", "required": False, "desc": "新内容"},
        "assignee": {"type": "str", "required": False, "desc": "负责人"},
        "due_date": {"type": "str", "required": False, "desc": "YYYY-MM-DD"},
        "priority": {"type": "str", "required": False, "desc": "low|medium|high"},
        "status": {"type": "str", "required": False, "desc": "pending|confirmed|done|dismissed"},
    },
    sensitive=True, handler=_update_action_item,
))
_reg(ToolSpec(
    name="create_share_link",
    description="为会议创建只读分享链接（对外暴露数据，敏感操作）",
    params={
        "meeting_id": {"type": "str", "required": True, "desc": "会议UUID"},
        "allow_download": {"type": "bool", "required": False, "desc": "是否允许下载", "default": True},
        "expires_in_days": {"type": "int", "required": False, "desc": "有效期天数，空=永久"},
    },
    sensitive=True, handler=_create_share_link,
))
_reg(ToolSpec(
    name="export_meeting",
    description="导出会议为 md/json/docx/pdf（敏感操作）",
    params={
        "meeting_id": {"type": "str", "required": True, "desc": "会议UUID"},
        "format": {"type": "str", "required": False, "desc": "md|json|docx|pdf", "default": "md"},
    },
    sensitive=True, handler=_export_meeting,
))


SENSITIVE_TOOLS: set[str] = {s.name for s in TOOLS.values() if s.sensitive}


def tool_catalog() -> str:
    """生成给 planner LLM 的工具清单文本"""
    lines = []
    for s in TOOLS.values():
        params = ", ".join(
            f"{p['name']}:{p['type']}" + ("" if p["required"] else "?")
            for p in [dict(name=k, **v) for k, v in s.params.items()]
        )
        flag = "【敏感·需确认】" if s.sensitive else ""
        lines.append(f"- {s.name}({params}) {flag}: {s.description}")
    return "\n".join(lines)


async def dispatch(ctx: AgentContext, name: str, args: dict) -> dict:
    """按名分发工具调用；未知工具/异常均返回结构化错误，不抛出"""
    spec = TOOLS.get(name)
    if not spec:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        return await spec.handler(ctx, args or {})
    except Exception as e:  # noqa: BLE001 - 工具层统一兜底，交给 reporter 解释
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}