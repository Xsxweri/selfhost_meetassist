"""对指定用户的所有会议同步跑记忆抽取（绕过 Celery，用于评测造数）。
用法: uv run python scripts/seed_memories.py a@b.com
前置: Ollama(qwen2.5:7b + bge-m3) 在跑、DB 在跑。
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.meeting import Meeting
from app.models.user import User
from app.services.memory_service import MemoryService


async def main(email: str):
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not u:
            raise SystemExit(f"用户不存在: {email}")
        ms = (await db.execute(select(Meeting).where(Meeting.owner_id == u.id))).scalars().all()
        print(f"待抽取会议数: {len(ms)}")
        svc = MemoryService(db)
        for m in ms:
            r = await svc.ingest_from_meeting(m.id)
            print(f"  {m.title}  ->  {r}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "a@b.com"))