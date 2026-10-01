import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.agent.graph import build_graph
from app.agent.llm import chat
from app.core.config import get_settings
from app.curd.conversation_thread import bump_turn, get_thread, upsert_thread
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.agent import AgentChatIn, AgentChatOut, AgentResumeIn

router = APIRouter(prefix="/agent", tags=["Agent"])
settings = get_settings()

_graph = None


def get_graph(app=None):
    """优先用 lifespan 预建的图（含配置的 checkpointer）；否则懒建内存版图（测试/降级）"""
    global _graph
    if app is not None:
        g = getattr(app.state, "graph", None)
        if g is not None:
            return g
    if _graph is None:
        _graph = build_graph()
    return _graph


def _shape(thread_id: str, result: dict) -> AgentChatOut:
    interrupts = result.get("__interrupt__")
    if interrupts:
        return AgentChatOut(
            thread_id=thread_id, status="awaiting_confirmation",
            confirmation=interrupts[0].value,
        )
    return AgentChatOut(
        thread_id=thread_id, status=result.get("status", "done"),
        report=result.get("final_report", ""),
    )


async def _roll_summary(older: list, prev: str | None) -> str | None:
    """把较早轮次压缩进滚动摘要（失败降级为保留旧摘要，不阻断）"""
    text = "\n".join(f"{h.get('role')}: {h.get('content')}" for h in older)
    prompt = (
        f"已有摘要：\n{prev or '（无）'}\n\n新增对话：\n{text}\n\n"
        "合并压缩为中文要点，≤200字，只输出摘要正文。"
    )
    try:
        s = await chat(prompt, system="你是对话摘要器")
        return (s or "").strip() or prev
    except Exception:  # noqa: BLE001
        return prev


@router.post("/chat", response_model=AgentChatOut)
async def agent_chat(
    payload: AgentChatIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agent 对话入口：理解目标 → RAG 召回 → 规划 → 执行 → 汇报；敏感操作中断等待确认"""
    thread_id = payload.thread_id or str(uuid.uuid4())
    existing = await get_thread(db, thread_id)
    if existing and existing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Thread not owned by current user")
    thread = await upsert_thread(
        db, thread_id=thread_id, owner_id=current_user.id, title=payload.message[:60]
    )

    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "owner_id": str(current_user.id),
        "user_id": str(current_user.id),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "goal": payload.message,
        "history": [{"role": "user", "content": payload.message}],
    }
    result = await get_graph(request.app).ainvoke(input_state, config=config)

    history = result.get("history") or []
    new_summary = None
    if thread.turn_count + 1 >= settings.THREAD_SUMMARY_THRESHOLD and len(history) > 6:
        new_summary = await _roll_summary(history[:-6], thread.rolling_summary)
    await bump_turn(db, thread, new_summary=new_summary)
    return _shape(thread_id, result)


def _sse(event: str, data:dict) -> str:
    """格式化SSE事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def agent_chat_stream(
        payload: AgentChatIn,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Agent 对话 SSE 流式输出"""
    thread_id = payload.thread_id or str(uuid.uuid4())
    existing = await get_thread(db, thread_id)
    if existing and existing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Thread not owned by current user")
    thread = await upsert_thread(
        db, thread_id=thread_id, owner_id=current_user.id, title=payload.message[:60]
    )
    graph = get_graph(request.app)
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "owner_id": str(current_user.id),
        "user_id": str(current_user.id),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "goal": payload.message,
        "history": [{"role": "user", "content": payload.message}],
    }
    prev_summary = thread.rolling_summary
    turn_count = thread.turn_count

    async def _gen():
        yield _sse("start", {"thread_id": thread_id})
        try:
            async for chunk in graph.astream(input_state, config=config, stream_mode="updates"):
                for node in chunk:
                    if node != "__interrupt__":
                        yield _sse("node", {"node": node, "status": "done"})
            # 流结束：区分「被 interrupt 暂停」还是「正常完成」
            state = await graph.aget_state(config)
            hit_interrupt = False
            for task in getattr(state, "tasks", []):
                for intr in getattr(task, "interrupts", ()):
                    yield _sse("confirmation", {"thread_id": thread_id, "confirmation": intr.value})
                    hit_interrupt = True
            if hit_interrupt:
                return
            values = state.values or {}
            history = values.get("history") or []
            yield _sse("done", {"thread_id": thread_id, "status": values.get("status", "done"), "report": values.get("final_report", "")})
            # 轮次计数 + 滚动摘要
            new_summary = None
            if turn_count + 1 >= settings.THREAD_SUMMARY_THRESHOLD and len(history) > 6:
                new_summary = await _roll_summary(history[:-6], prev_summary)
            async with AsyncSessionLocal() as s:
                t = await get_thread(s, thread_id)
                if t:
                    await bump_turn(s, t, new_summary=new_summary)
        except Exception as e:
            yield _sse("error", {"detail": f"{type(e).__name__}: {e}"})
    return StreamingResponse(_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/resume", response_model=AgentChatOut)
async def agent_resume(
    payload: AgentResumeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """人工确认闸门回调：先查库校验 thread 归属（防越权批准），再恢复图执行"""
    thread = await get_thread(db, payload.thread_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Thread not found or expired")
    if thread.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Thread not owned by current user")

    config = {"configurable": {"thread_id": payload.thread_id}}
    result = await get_graph(request.app).ainvoke(
        Command(resume={"approved": payload.approved}), config=config
    )
    return _shape(payload.thread_id, result)