"""性能基准：LLM 延迟/tokens + embedding 延迟 + pgvector/pg_trgm 检索延迟。

采集口径：
- LLM(/api/chat)：墙钟延迟 + prompt/completion tokens + tokens/s（纪要 & 抽取两种 prompt，直连 Ollama 拿 usage）
- embedding(/api/embed)：墙钟延迟 p50/p95 + 维度
- pgvector find_similar：纯 DB 延迟 p50/p95（复用同一 query 向量，隔离 embedding 耗时）
- pg_trgm search_by_keyword：纯 DB 延迟 p50/p95
- MemoryService.recall：端到端 p50/p95（含 embedding + 双路 + RRF）

用法：
    uv run python scripts/bench_perf.py --owner a@b.com
    uv run python scripts/bench_perf.py --owner a@b.com --rounds 50 --llm-rounds 5
"""
import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.core.prompts import render_prompt
from app.curd import memory as memory_crud
from app.db.session import AsyncSessionLocal
from app.models.meeting import Meeting
from app.models.user import User
from app.services.memory_service import MemoryService

settings = get_settings()
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

SAMPLE_TEXT = (
    "本次周会决议：批准Q3市场预算500万元，由张总负责审批；产品V2上线时间定为9月30日；"
    "李四需在下周五前提交合规报告；团队例会固定在每周三上午；客户A合同金额120万元，续约意向明确。"
)
QUERIES = ["Q3市场预算批了多少钱", "谁负责提交合规报告", "客户A合同金额", "产品上线时间"]


def pct(xs: list[float], p: float) -> float:
    """线性插值百分位（无 numpy 依赖）"""
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] if f == c else xs[f] + (xs[c] - xs[f]) * (k - f)


async def probe_chat(client: httpx.AsyncClient, prompt: str, *, json_mode=False, temperature=None) -> dict:
    """直连 Ollama /api/chat，payload 与 LlmService._call_llm 完全一致，额外采集 usage"""
    payload = {"model": settings.LLM_MODEL,
               "messages": [{"role": "user", "content": prompt}], "stream": False}
    if json_mode:
        payload["format"] = "json"
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    t0 = time.perf_counter()
    r = await client.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload)
    r.raise_for_status()
    wall = (time.perf_counter() - t0) * 1000
    d = r.json()
    eval_ms = d.get("eval_duration", 0) / 1e6
    ct = d.get("eval_count", 0)
    return {
        "wall_ms": wall,
        "prompt_tokens": d.get("prompt_eval_count", 0),
        "completion_tokens": ct,
        "eval_ms": eval_ms,
        "tps": (ct / (eval_ms / 1000)) if eval_ms > 0 else 0.0,
    }


async def probe_embed(client: httpx.AsyncClient, text: str):
    t0 = time.perf_counter()
    r = await client.post(f"{settings.OLLAMA_BASE_URL}/api/embed",
                          json={"model": settings.EMBEDDING_MODEL, "input": text})
    r.raise_for_status()
    wall = (time.perf_counter() - t0) * 1000
    d = r.json()
    emb = d["embeddings"][0] if "embeddings" in d else d["embedding"]
    return wall, emb


async def bench_llm(client: httpx.AsyncClient, text: str, rounds: int):
    summary_prompt = render_prompt("summary_user", transcript=text[:8000])
    extract_prompt = render_prompt("memory_extract_user", transcript=text[:8000])
    await probe_chat(client, "hi")  # warmup，排除模型冷启动

    print("\n=== LLM 延迟 / tokens（/api/chat）===")
    for label, prompt, jm, temp in [
        ("纪要生成 generate_summary", summary_prompt, False, None),
        ("记忆抽取 extract_memories", extract_prompt, True, 0.0),
    ]:
        rows = [await probe_chat(client, prompt, json_mode=jm, temperature=temp) for _ in range(rounds)]
        walls = [r["wall_ms"] for r in rows]
        pt = sum(r["prompt_tokens"] for r in rows) / rounds
        ct = sum(r["completion_tokens"] for r in rows) / rounds
        tps = sum(r["tps"] for r in rows) / rounds
        print(f"  {label}")
        print(f"    墙钟 p50={pct(walls,0.5):8.1f}ms  p95={pct(walls,0.95):8.1f}ms  max={max(walls):8.1f}ms")
        print(f"    tokens 输入≈{pt:.0f}  输出≈{ct:.0f}   生成速度≈{tps:.1f} tok/s")


async def bench_embed(client: httpx.AsyncClient, rounds: int) -> list[float]:
    await probe_embed(client, "warmup")
    walls, emb = [], None
    for q in QUERIES * (rounds // len(QUERIES) + 1):
        if len(walls) >= rounds:
            break
        w, emb = await probe_embed(client, q)
        walls.append(w)
    print("\n=== Embedding 延迟（/api/embed, bge-m3）===")
    print(f"    墙钟 p50={pct(walls,0.5):7.2f}ms  p95={pct(walls,0.95):7.2f}ms  max={max(walls):7.2f}ms  维度={len(emb) if emb else 0}")
    return walls


async def bench_db(owner_id, rounds: int):
    async with AsyncSessionLocal() as db:
        svc = MemoryService(db)
        _, qvec = await probe_embed(httpx.AsyncClient(timeout=30.0), QUERIES[0])

        vec_ms, kw_ms, recall_ms = [], [], []
        for i in range(rounds):
            q = QUERIES[i % len(QUERIES)]

            t0 = time.perf_counter()
            await memory_crud.find_similar(db, owner_id=owner_id, embedding=qvec,
                                           limit=settings.MEMORY_TOP_K * 2,
                                           min_similarity=settings.MEMORY_RECALL_MIN_SIM)
            vec_ms.append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            await memory_crud.search_by_keyword(db, owner_id=owner_id, query=q,
                                                limit=settings.MEMORY_TOP_K * 2)
            kw_ms.append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            await svc.recall(q, owner_id, limit=settings.MEMORY_TOP_K)
            recall_ms.append((time.perf_counter() - t0) * 1000)

    print(f"\n=== DB 检索延迟（{rounds} 轮，owner 隔离）===")
    for label, xs in [("pgvector find_similar", vec_ms),
                      ("pg_trgm  search_by_keyword", kw_ms),
                      ("recall 端到端(含embed+RRF)", recall_ms)]:
        print(f"  {label:30s} p50={pct(xs,0.5):7.2f}ms  p95={pct(xs,0.95):7.2f}ms  max={max(xs):7.2f}ms")


async def main(email: str, rounds: int, llm_rounds: int):
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not u:
            raise SystemExit(f"用户不存在: {email}")
        meetings = (await db.execute(select(Meeting).where(Meeting.owner_id == u.id))).scalars().all()
        best = max(meetings, key=lambda m: len((m.summary or "") + (m.transcript or "")), default=None)
        text = ((best.summary or "") + "\n\n" + (best.transcript or "")) if best else SAMPLE_TEXT
        owner_id = u.id
    src = f"真实：{best.title}" if best else "内置样例"
    print(f"owner={email}  LLM样本会议=（{src}）  文本长={len(text)}")

    async with httpx.AsyncClient(timeout=180.0) as client:
        await bench_llm(client, text, llm_rounds)
        await bench_embed(client, rounds)
    await bench_db(owner_id, rounds)

    print("\n提示：LLM 延迟随输入文本长度线性上升；recall 端到端 ≈ embedding + max(向量,关键词) + RRF。")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--owner", default="a@b.com")
    p.add_argument("--rounds", type=int, default=30, help="embedding/DB 检索重复轮数")
    p.add_argument("--llm-rounds", type=int, default=3, help="LLM 调用轮数（较慢，勿设太大）")
    a = p.parse_args()
    asyncio.run(main(a.owner, a.rounds, a.llm_rounds))