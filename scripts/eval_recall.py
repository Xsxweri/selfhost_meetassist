"""记忆检索质量评测：Recall@K / Precision@K / MRR / nDCG / Hit Rate + RRF 融合增益。

前置：真实库已有记忆数据、Ollama(bge-m3) 在跑。
用法：
  uv run python scripts/eval_recall.py --golden scripts/golden_recall.json --k 6
  uv run python scripts/eval_recall.py --dump --owner me@test.com   # 导出记忆清单辅助标注
"""
import argparse
import asyncio
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import get_settings
from app.curd import memory as memory_crud
from app.db.session import AsyncSessionLocal
from app.models.memory import Memory
from app.models.user import User
from app.services.llm_service import LlmService
from app.services.memory_service import _rrf


settings = get_settings()
MODES = ("vector", "keyword", "hybrid")


async def _owner_id(db, email: str):
    res = await db.execute(select(User).where(User.email == email))
    u = res.scalar_one_or_none()
    if not u:
        raise SystemExit(f"用户不存在: {email}")
    return u.id


async def retrieve(db, owner_id, query, qvec, mode, k,min_sim):
    """按模式取 Top-K；向量/关键词分别取 k*2 再 RRF 融合，与线上 recall 一致"""
    if mode == "vector":
        if not qvec:
            return []
        return await memory_crud.find_similar(
            db, owner_id=owner_id, embedding=qvec, limit=k,
            min_similarity=min_sim,
        )
    if mode == "keyword":
        return await memory_crud.search_by_keyword(
            db, owner_id=owner_id, query=query, limit=k,
        )
    vec = []
    if qvec:
        vec = await memory_crud.find_similar(
            db, owner_id=owner_id, embedding=qvec, limit=k * 2,
            min_similarity=min_sim,
        )
    kw = await memory_crud.search_by_keyword(
        db, owner_id=owner_id, query=query, limit=k * 2,
    )
    return _rrf([vec, kw])[:k]


def _eval_case(hits, golds, k):
    hits = hits[:k]
    contents = [h.get("content") or "" for h in hits]
    rels = [any(g in c for g in golds) for c in contents]

    hit_golds = {g for g in golds if any(g in c for c in contents)}
    recall = len(hit_golds) / len(golds) if golds else 0.0
    precision = sum(rels) / k if k else 0.0
    hit_rate = 1.0 if any(rels) else 0.0

    rr = 0.0
    for i, r in enumerate(rels):
        if r:
            rr = 1.0 / (i + 1)
            break

    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rels))
    n_rel = min(sum(1 for r in rels if r), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_rel))
    ndcg = dcg / idcg if idcg else 0.0
    return {"recall": recall, "precision": precision, "hit": hit_rate, "rr": rr, "ndcg": ndcg}


def _mean(rows, key):
    return sum(r[key] for r in rows) / len(rows) if rows else 0.0


async def run(args):
    data = json.load(open(args.golden, encoding="utf-8"))
    default_owner = data.get("owner_email") or args.owner
    cases = data["cases"]
    async with AsyncSessionLocal() as db:
        llm = LlmService(db)
        per_mode = {m: [] for m in MODES}
        for case in cases:
            golds = case.get("gold_contains") or case.get("gold") or []
            if not golds:
                continue
            owner = case.get("owner_email") or default_owner
            oid = await _owner_id(db, owner)
            qvec = await llm._get_embedding(case["query"])
            for m in MODES:
                hits = await retrieve(db, oid, case["query"], qvec, m, args.k, args.min_sim)
                per_mode[m].append(_eval_case(hits, golds, args.k))

    print(f"\n=== 记忆检索评测（{len(cases)} cases, K={args.k}）===")
    print(f"{'mode':<9}{'Recall@K':>10}{'Prec@K':>9}{'MRR':>8}{'nDCG':>8}{'Hit':>7}")
    summary = {}
    for m in MODES:
        rows = per_mode[m]
        summary[m] = {
            "Recall@K": _mean(rows, "recall"), "Prec@K": _mean(rows, "precision"),
            "MRR": _mean(rows, "rr"), "nDCG": _mean(rows, "ndcg"), "Hit": _mean(rows, "hit"),
        }
        s = summary[m]
        print(f"{m:<9}{s['Recall@K']:>10.3f}{s['Prec@K']:>9.3f}{s['MRR']:>8.3f}"
              f"{s['nDCG']:>8.3f}{s['Hit']:>7.3f}")

    best_single = max(summary["vector"]["MRR"], summary["keyword"]["MRR"])
    print(f"\nRRF 融合增益(MRR): {summary['hybrid']['MRR'] - best_single:+.3f} "
          f"(hybrid {summary['hybrid']['MRR']:.3f} vs best-single {best_single:.3f})")


async def dump(args):
    async with AsyncSessionLocal() as db:
        oid = await _owner_id(db, args.owner)
        res = await db.execute(
            select(Memory).where(
                Memory.owner_id == oid, Memory.deleted_at.is_(None),
                Memory.valid_to.is_(None), Memory.superseded_by.is_(None),
            ).order_by(Memory.created_at.desc())
        )
        for m in res.scalars().all():
            print(f"{str(m.id)}  [{m.kind}] {m.subject or '-'}  {(m.content or '')[:60]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--golden", help="golden set JSON 路径")
    p.add_argument("--k", type=int, default=settings.MEMORY_TOP_K)
    p.add_argument("--min-sim", type=float, default=settings.MEMORY_RECALL_MIN_SIM, help="向量路相似度下限，调高可逼出 RRF 融合增益")
    p.add_argument("--owner", help="默认 owner_email")
    p.add_argument("--dump", action="store_true", help="导出记忆清单辅助标注")
    args = p.parse_args()
    if args.dump:
        if not args.owner:
            raise SystemExit("--dump 需要 --owner")
        asyncio.run(dump(args))
    else:
        if not args.golden:
            raise SystemExit("需要 --golden")
        asyncio.run(run(args))


if __name__ == "__main__":
    main()