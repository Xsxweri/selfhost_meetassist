import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    # 身份与请求元数据（可序列化，跨 interrupt 持久）
    owner_id: str
    user_id: str
    ip: str | None
    user_agent: str | None
    # 对话
    goal: str
    history: Annotated[list, operator.add]   # 跨轮累积
    # 记忆层
    memory_context: list    # recall 节点注入的长期记忆（RAG）
    thread_summary: str     # 会话滚动摘要
    # 规划与执行
    plan: list          # [{"tool","args","reason"}]
    cursor: int         # 当前步骤下标
    results: list       # 每步结果（planner 每轮重置）
    gate_decision: str  # "approve" | "deny"
    # 输出
    final_report: str
    status: str
