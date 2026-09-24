from typing import Any, Optional
from pydantic import BaseModel, Field


# Agent 输入
class AgentChatIn(BaseModel):
    message: str = Field(..., min_length=1, description="用户目标/指令")
    thread_id: Optional[str] = Field(None, description="会话线程ID，续聊时传入")


# 恢复会话输入
class AgentResumeIn(BaseModel):
    thread_id: str = Field(..., description="待确认的会话线程ID")
    approved: bool = Field(..., description="是否批准敏感操作")


# 确认输出
class ConfirmationOut(BaseModel):
    type: str = "confirm"
    tool: str
    args: dict[str, Any] = {}
    reason: str = ""
    message: str = ""


# Agent 输出
class AgentChatOut(BaseModel):
    thread_id: str
    status: str                       # done | awaiting_confirmation
    report: Optional[str] = None
    confirmation: Optional[ConfirmationOut] = None