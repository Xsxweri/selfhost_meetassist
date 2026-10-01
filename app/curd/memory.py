import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory


async def create_memory(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    content: str,
    kind: str = "fact",
    subject: str | None = None,
    meeting_id: uuid.UUID | None = None,
    embedding: list[float] | None = None,
    importance: float = 0.5,
    confidence: float = 1.0,
    source_transcript_id: uuid.UUID | None = None,
    valid_from: datetime | None = None,
) -> Memory:
    mem = Memory(
        owner_id=owner_id, content=content, kind=kind, subject=subject,
        meeting_id=meeting_id, embedding=embedding, importance=importance,
        confidence=confidence, source_transcript_id=source_transcript_id,
        valid_from=valid_from,
    )
    db.add(mem)
    await db.commit()
    await db.refresh(mem)
    return mem


async def get_memory(
    db: AsyncSession, memory_id: uuid.UUID, owner_id: uuid.UUID
) -> Memory | None:
    """按 id + owner 取记忆（排除软删除），越权返回 None"""
    result = await db.execute(
        select(Memory).where(
            Memory.id == memory_id,
            Memory.owner_id == owner_id,
            Memory.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_memories(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    kind: str | None = None,
    subject: str | None = None,
    include_superseded: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[Memory]:
    stmt = select(Memory).where(
        Memory.owner_id == owner_id, Memory.deleted_at.is_(None)
    )
    if kind is not None:
        stmt = stmt.where(Memory.kind == kind)
    if subject is not None:
        stmt = stmt.where(Memory.subject == subject)
    if not include_superseded:
        stmt = stmt.where(Memory.valid_to.is_(None), Memory.superseded_by.is_(None))
    stmt = stmt.order_by(Memory.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_similar(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    embedding: list[float],
    limit: int = 6,
    min_similarity: float = 0.0,
    kind: str | None = None,
    subject: str | None = None,
    since: datetime | None = None,
) -> list[dict]:
    """向量近邻检索（仅当前 owner 的有效记忆）；混合 RRF 检索"""
    clauses = [
        "owner_id = :owner",
        "deleted_at IS NULL",
        "valid_to IS NULL",
        "superseded_by IS NULL",
        "embedding IS NOT NULL",
        "1 - (embedding <=> CAST(:qvec AS vector)) >= :minsim",
    ]
    params: dict = {
        "qvec": str(embedding), "owner": owner_id,
        "minsim": min_similarity, "lim": limit,
    }
    if kind is not None:
        clauses.append("kind = :kind")
        params["kind"] = kind
    if subject is not None:
        clauses.append("subject = :subject")
        params["subject"] = subject
    if since is not None:
        clauses.append("created_at >= :since")
        params["since"] = since

    sql = f"""
          SELECT id, kind, subject, content, meeting_id, importance, created_at,
                 1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
          FROM memories
          WHERE {" AND ".join(clauses)}
          ORDER BY embedding <=> CAST(:qvec AS vector)
          LIMIT :lim
      """
    result = await db.execute(text(sql), params)
    return [dict(row) for row in result.mappings().fetchall()]


async def search_by_keyword(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    query: str,
    limit: int = 6,
    kind: str | None = None,
    subject: str | None = None,
    since: datetime | None = None,
) -> list[dict]:
    """关键词检索（pg_trgm）：ILIKE 子串命中 + 三元组相似度排序，仅当前 owner 的有效记忆"""
    clauses = [
        "owner_id = :owner",
        "deleted_at IS NULL",
        "valid_to IS NULL",
        "superseded_by IS NULL",
        "(content ILIKE :like OR subject ILIKE :like)",
    ]
    params: dict = {"owner": owner_id, "like": f"%{query}%", "q": query, "lim": limit}
    if kind is not None:
        clauses.append("kind = :kind")
        params["kind"] = kind
    if subject is not None:
        clauses.append("subject = :subject")
        params["subject"] = subject
    if since is not None:
        clauses.append("created_at >= :since")
        params["since"] = since

    sql = f"""
          SELECT id, kind, subject, content, meeting_id, importance, created_at,
                 similarity(content, CAST(:q AS text)) AS kw_sim
          FROM memories
          WHERE {" AND ".join(clauses)}
          ORDER BY kw_sim DESC, created_at DESC
          LIMIT :lim
      """
    result = await db.execute(text(sql), params)
    return [dict(row) for row in result.mappings().fetchall()]


async def supersede_memory(
    db: AsyncSession, old: Memory, new_memory_id: uuid.UUID
) -> Memory:
    """旧记忆被新事实取代：打 valid_to + superseded_by，形成演进链"""
    old.valid_to = datetime.now(timezone.utc)
    old.superseded_by = new_memory_id
    await db.commit()
    await db.refresh(old)
    return old


async def touch_access(db: AsyncSession, mem: Memory) -> Memory:
    """命中强化：访问计数 +1"""
    mem.access_count = (mem.access_count or 0) + 1
    mem.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(mem)
    return mem


async def soft_delete_memory(db: AsyncSession, mem: Memory) -> None:
    mem.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def update_memory(db: AsyncSession, mem: Memory, **fields) -> Memory:
    """更新记忆可变字段（kind/subject/content/importance）；fields已由API层exclude_unset过滤"""
    for key, value in fields.items():
        if hasattr(mem, key):
            setattr(mem, key, value)
    await db.commit()
    await db.refresh(mem)
    return mem


async def get_memory_chain(
    db: AsyncSession, memory_id: uuid.UUID, owner_id: uuid.UUID
) -> list[Memory]:
    """获取记忆完整演进链（最旧→最新），含被supersede的历史版本，仅当前 owner"""
    start = await db.execute(
        select(Memory).where(
            Memory.id == memory_id,
            Memory.owner_id == owner_id,
            Memory.deleted_at.is_(None),
        )
    )
    node = start.scalar_one_or_none()
    if not node:
        return []
    # 先顺着superseded_by走到最新版本
    seen = {node.id}
    cur = node
    while cur.superseded_by and cur.superseded_by not in seen:
        nxt = await db.execute(
            select(Memory).where(
                Memory.id == cur.superseded_by, Memory.owner_id == owner_id
            )
        )
        nxt_node = nxt.scalar_one_or_none()
        if not nxt_node:
            break
        seen.add(nxt_node.id)
        cur = nxt_node
    # 再从最新反查superseded_by==cur.id逐层收集到最旧
    chain = [cur]
    visited = {cur.id}
    while True:
        prev = await db.execute(
            select(Memory).where(
                Memory.superseded_by == cur.id,
                Memory.owner_id == owner_id,
                Memory.deleted_at.is_(None),
            )
        )
        prev_node = prev.scalars().first()
        if not prev_node or prev_node.id in visited:
            break
        visited.add(prev_node.id)
        chain.append(prev_node)
        cur = prev_node
    chain.reverse()
    return chain


async def archive_superseded(db: AsyncSession, *, before_days: int = 90) -> int:
    """
    软删除已被演进(valid_to 早于 cutoff)且超保留期的记忆，控制表膨胀。
    演进链保留before_days天供审计追溯，之后软删（deleted_at打标，非物理删除）。
    召回路径本就过滤superseded_by/valid_to，归档不影响检索，仅回收存储。
    返回归档行数。
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=before_days)
    stmt = (
        update(Memory)
        .where(
            Memory.superseded_by.is_not(None),
            Memory.valid_to.is_not(None),
            Memory.valid_to < cutoff,
            Memory.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0