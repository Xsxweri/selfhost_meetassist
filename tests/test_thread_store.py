import uuid

from app.curd.conversation_thread import (
    bump_turn, get_thread, list_threads, upsert_thread,
)


async def test_upsert_and_get(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    t = await upsert_thread(db_session, thread_id="th-1", owner_id=oid, title="预算会")
    assert t.thread_id == "th-1" and t.turn_count == 0 and t.title == "预算会"
    got = await get_thread(db_session, "th-1")
    assert got and got.owner_id == oid


async def test_upsert_idempotent(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    await upsert_thread(db_session, thread_id="th-2", owner_id=oid)
    t2 = await upsert_thread(db_session, thread_id="th-2", owner_id=oid)
    assert t2.turn_count == 0        # 不重复插入


async def test_bump_turn_and_summary(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    t = await upsert_thread(db_session, thread_id="th-3", owner_id=oid)
    t = await bump_turn(db_session, t)
    t = await bump_turn(db_session, t, new_summary="要点A")
    assert t.turn_count == 2 and t.rolling_summary == "要点A"


async def test_list_threads_owner_scoped(db_session, make_auth):
    a = await make_auth(); b = await make_auth()
    await upsert_thread(db_session, thread_id="a1", owner_id=uuid.UUID(a["user_id"]))
    await upsert_thread(db_session, thread_id="b1", owner_id=uuid.UUID(b["user_id"]))
    la = await list_threads(db_session, uuid.UUID(a["user_id"]))
    assert {t.thread_id for t in la} == {"a1"}