"""archive_superseded 归档逻辑：只软删超期演进链，不误伤保留期内/活跃记忆"""
import uuid
from datetime import datetime, timedelta, timezone

from app.curd import memory as memory_crud
from app.models.memory import Memory


async def _make_superseded(db, oid, old_content, new_content, valid_to):
    """造一条演进链：old 被 new 取代，并把 valid_to 回填为指定历史时间"""
    old = await memory_crud.create_memory(db, owner_id=oid, content=old_content, kind="fact")
    new = await memory_crud.create_memory(db, owner_id=oid, content=new_content, kind="fact")
    await memory_crud.supersede_memory(db, old, new.id)  # 默认写 valid_to=now
    old.valid_to = valid_to                              # 回填为历史演进时间
    await db.commit()
    return old, new


async def test_archive_only_stale_superseded(db_session, make_auth):
    """核心边界：超期(100天)归档、保留期内(10天)与活跃记忆均不动"""
    oid = uuid.UUID((await make_auth())["user_id"])
    now = datetime.now(timezone.utc)

    old_stale, new1 = await _make_superseded(
        db_session, oid, "旧结论A", "新结论A", now - timedelta(days=100)
    )
    old_recent, _ = await _make_superseded(
        db_session, oid, "旧结论B", "新结论B", now - timedelta(days=10)
    )
    active = await memory_crud.create_memory(
        db_session, owner_id=oid, content="活跃结论C", kind="fact"
    )

    n = await memory_crud.archive_superseded(db_session, before_days=90)
    assert n == 1  # 只有超期那条被归档

    # bulk update 用了 synchronize_session=False，须清 ORM 缓存再查真实库状态
    await db_session.refresh(old_stale)
    await db_session.refresh(old_recent)
    await db_session.refresh(active)

    assert old_stale.deleted_at is not None   # 超期演进链 → 已软删
    assert old_recent.deleted_at is None      # 保留期内 → 未动
    assert active.deleted_at is None         # 活跃记忆 → 未动
    # 审计字段保留，演进链仍可追溯
    assert old_stale.superseded_by == new1.id
    assert old_stale.valid_to is not None


async def test_archive_is_idempotent(db_session, make_auth):
    """幂等：已归档(deleted_at 非空)的记忆不再被重复处理"""
    oid = uuid.UUID((await make_auth())["user_id"])
    now = datetime.now(timezone.utc)
    await _make_superseded(db_session, oid, "旧", "新", now - timedelta(days=100))

    first = await memory_crud.archive_superseded(db_session, before_days=90)
    second = await memory_crud.archive_superseded(db_session, before_days=90)
    assert first == 1
    assert second == 0


async def test_archived_memory_invisible_to_reads(db_session, make_auth):
    """归档后软删生效于读路径：get_memory 查不到旧记忆，取代它的新记忆仍可见"""
    oid = uuid.UUID((await make_auth())["user_id"])
    now = datetime.now(timezone.utc)
    old, new = await _make_superseded(db_session, oid, "旧", "新", now - timedelta(days=100))

    await memory_crud.archive_superseded(db_session, before_days=90)

    assert await memory_crud.get_memory(db_session, old.id, oid) is None   # 软删 → 不可见
    assert await memory_crud.get_memory(db_session, new.id, oid) is not None  # 新记忆仍在