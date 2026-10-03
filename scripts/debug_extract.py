"""定位记忆抽取为空的原因：打印输入文本、LLM 原始返回、解析结果。
用法: uv run python scripts/debug_extract.py [meeting_id]
"""
import sys
import asyncio
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.prompts import render_prompt
from app.db.session import AsyncSessionLocal
from app.models.meeting import Meeting
from app.services.llm_service import LlmService

DEFAULT_MID = "3534be4f-b4eb-4302-a612-dd39202c2a55"


async def main(mid: str):
    async with AsyncSessionLocal() as db:
        m = await db.get(Meeting, uuid.UUID(mid))
        if not m:
            raise SystemExit(f"会议不存在: {mid}")
        text = "\n\n".join(x for x in [m.summary, m.transcript] if x).strip()
        print(f"=== 输入文本 (len={len(text)}) ===\n{text[:2000]}")
        prompt = render_prompt("memory_extract_user", transcript=text[:8000])
        raw = await LlmService(db)._call_llm(prompt, json_mode=True)
        print(f"\n=== LLM 原始输出 ===\n{raw}")
        print(f"\n=== 解析结果 ===\n{LlmService._parse_memories(raw)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MID))