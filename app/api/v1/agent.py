import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command

from app.api.deps import get_current_user
from app.agent.graph import build_graph
from app.models.user import User
from app.schemas.agent import AgentChatIn, AgentChatOut, AgentResumeIn

router = APIRouter(prefix="/agent", tags=["Agent"])

_graph = None
# thread_id -> user_id 归属表（进程内内存，与 InMemorySaver 同生命周期；多进程/重启后失效，换 Postgres checkpointer + 持久映射表）
_thread_owner: dict[str, str] = {}


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _assert_owner(thread_id: str, user_id: str) -> None:
    """断言线程归属"""
    owner = _thread_owner.get(thread_id)
    if owner is not None and owner != user_id:
        raise HTTPException(status_code=403, detail="Thread not owned by current user")


def _shape(thread_id: str, result: dict) -> AgentChatOut:
    """将中间结果转换为输出结果"""
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


@router.post("/chat", response_model=AgentChatOut)
async def agent_chat(
    payload: AgentChatIn,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Agent 对话入口：理解目标 → 规划 → 执行 → 汇报；敏感操作中断等待确认"""
    thread_id = payload.thread_id or str(uuid.uuid4())
    _assert_owner(thread_id, str(current_user.id))
    _thread_owner[thread_id] = str(current_user.id)
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "owner_id": str(current_user.id),
        "user_id": str(current_user.id),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "goal": payload.message,
        "history": [{"role": "user", "content": payload.message}],
    }
    result = await get_graph().ainvoke(input_state, config=config)
    return _shape(thread_id, result)


@router.post("/resume", response_model=AgentChatOut)
async def agent_resume(
    payload: AgentResumeIn,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """人工确认闸门回调：批准/拒绝后恢复图执行先校验 thread 归属，防越权批准）"""
    _assert_owner(payload.thread_id, str(current_user.id))
    if payload.thread_id not in _thread_owner:
        raise HTTPException(status_code=403, detail="Thread not found or expired")
    config = {"configurable": {"thread_id": payload.thread_id}}
    result = await get_graph().ainvoke(
        Command(resume={"approved": payload.approved}), config=config
    )
    return _shape(payload.thread_id, result)