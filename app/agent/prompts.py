import json
from app.core.prompts import load_prompt, render_prompt


def plan_system() -> str:
    return load_prompt("agent_plan_system")


def report_system() -> str:
    return load_prompt("agent_report_system")


def build_plan_prompt(catalog: str, history: list[dict], goal: str) -> str:
    """生成会议计划"""
    recent = history[-10:] if history else []
    hist_txt = "\n".join(f"{h.get('role')}: {h.get('content')}" for h in recent) or "（无）"
    return render_prompt("agent_plan_user", catalog=catalog, history=hist_txt, goal=goal)


def build_report_prompt(goal: str, results: list[dict]) -> str:
    """生成会议纪要"""
    return render_prompt(
        "agent_report_user",
        goal=goal,
        results=json.dumps(results, ensure_ascii=False, indent=2),
    )
