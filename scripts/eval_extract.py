"""记忆抽取质量评测：抽取产出 + 记忆库健康度 + 演进链 + 抽样核对。

模式：
- 默认 snapshot：只读统计现有 memories 分布（安全，不改库）。
- --ingest：对 owner 的会议跑 ingest_from_meeting，测抽取产出(created/superseded)与耗时（会写库）。
- --sample N：抽样打印 N 条有效记忆，人工核对准确性/幻觉/kind 是否正确。

用法：
    uv run python scripts/eval_extract.py --owner a@b.com
    uv run python scripts/eval_extract.py --owner a@b.com --ingest --sample 10
"""
import argparse
import asyncio
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.meeting import Meeting
from app.models.memory import Memory
from app.models.user import User
from app.services.memory_service import MemoryService


async def _owner_id(db, email):
    u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not u:
        raise SystemExit(f"用户不存在: {email}")
    return u.id


async def ingest_eval(db, oid):
    ms = (await db.execute(
        select(Meeting).where(Meeting.owner_id == oid, Meeting.deleted_at.is_(None))
    )).scalars().all()
    print(f"\n=== 抽取过程评测（{len(ms)} 场会议）===")
    if not ms:
        print("  该用户无会议。")
        return
    svc = MemoryService(db)
    tot_c = tot_s = 0
    tot_t = 0.0
    for m in ms:
        t0 = time.time()
        r = await svc.ingest_from_meeting(m.id)
        dt = time.time() - t0
        c, s = r.get("created", 0), r.get("superseded", 0)
        flag = r.get("skipped") or r.get("error") or ""
        tot_c += c
        tot_s += s
        tot_t += dt
        tail = f"  [{flag}]" if flag else ""
        print(f"  {m.title[:22]:22s} created={c:<3d} superseded={s:<3d} {dt:5.1f}s{tail}")
    if tot_c:
        print(f"\n  合计 created={tot_c}  superseded={tot_s}  去重率={tot_s / tot_c:.1%}")
    else:
        print("\n  合计 created=0（无内容可抽取）")
    print(f"  抽取总耗时 {tot_t:.1f}s  平均每会议 {tot_t / len(ms):.1f}s")
    print("  注：ingest 会写库；对同一批会议重跑 --ingest 可观察 supersede 演进链增长。")


async def snapshot(db, oid):
    mems = (await db.execute(select(Memory).where(Memory.owner_id == oid))).scalars().all()
    total = len(mems)
    print(f"\n=== 记忆库快照（共 {total} 条）===")
    if not total:
        print("  记忆库为空。先跑 --ingest 抽取。")
        return
    active = [m for m in mems if not m.deleted_at and not m.valid_to and not m.superseded_by]
    superseded = [m for m in mems if m.superseded_by or m.valid_to]
    deleted = [m for m in mems if m.deleted_at]
    with_emb = [m for m in mems if m.embedding is not None]
    with_subj = [m for m in mems if m.subject]
    imps = [m.importance for m in mems if m.importance is not None]
    kinds = Counter(m.kind for m in mems)
    per_meeting = Counter(m.meeting_id for m in mems if m.meeting_id)

    print(f"  有效(active)      : {len(active):3d}  ({len(active) / total:.1%})")
    print(f"  已演进(superseded): {len(superseded):3d}  ({len(superseded) / total:.1%})")
    print(f"  已软删除          : {len(deleted):3d}  ({len(deleted) / total:.1%})")
    print(f"  embedding 覆盖    : {len(with_emb)}/{total}  ({len(with_emb) / total:.1%})")
    print(f"  subject 覆盖      : {len(with_subj)}/{total}  ({len(with_subj) / total:.1%})")
    if imps:
        print(f"  importance        : 均值 {sum(imps) / len(imps):.3f}  min {min(imps):.2f}  max {max(imps):.2f}")
    print("  kind 分布         :")
    for k, v in kinds.most_common():
        print(f"      {k:12s} {v:3d}  ({v / total:.1%})")
    if per_meeting:
        cnts = list(per_meeting.values())
        print(f"  覆盖会议数        : {len(per_meeting)}")
        print(f"  每会议记忆数      : 均值 {sum(cnts) / len(cnts):.1f}  max {max(cnts)}  min {min(cnts)}")


async def print_sample(db, oid, n):
    mems = (await db.execute(
        select(Memory).where(
            Memory.owner_id == oid, Memory.deleted_at.is_(None),
            Memory.valid_to.is_(None), Memory.superseded_by.is_(None),
        ).order_by(Memory.created_at.desc()).limit(n)
    )).scalars().all()
    print(f"\n=== 抽样 {len(mems)} 条有效记忆（人工核对：忠于原文？kind 对？有无幻觉？）===")
    for m in mems:
        print(f"  [{m.kind:10s}] subj={str(m.subject)[:12]:12s} imp={m.importance:.2f} :: {m.content[:70]}")


async def run(email, do_ingest, sample):
    async with AsyncSessionLocal() as db:
        oid = await _owner_id(db, email)
        if do_ingest:
            await ingest_eval(db, oid)
        await snapshot(db, oid)
        if sample:
            await print_sample(db, oid, sample)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--owner", default="a@b.com")
    p.add_argument("--ingest", action="store_true", help="对会议重新跑抽取（会写库）")
    p.add_argument("--sample", type=int, default=10, help="抽样打印 N 条记忆，0=不打印")
    args = p.parse_args()
    asyncio.run(run(args.owner, args.ingest, args.sample))


if __name__ == "__main__":
    main()