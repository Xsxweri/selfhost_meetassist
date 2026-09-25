import uuid

from app.curd.memory import (
    create_memory, find_similar, get_memory, list_memories,
    soft_delete_memory, supersede_memory,
)

_V1 = [1.0] + [0.0] * 1023
_V2 = [0.0] * 1023 + [1.0]


async def test_create_and_get_memory(db_session, make_auth):
    u = await make_auth()
    oid = uuid.UUID(u["user_id"])
    m = await create_memory(db_session, owner_id=oid, content="预算批准500万",
                            kind="decision", subject="预算", embedding=_V1, importance=0.8)
    got = await get_memory(db_session, m.id, oid)
    assert got and got.content == "预算批准500万" and got.kind == "decision"


async def test_cross_user_isolation(db_session, make_auth):
    a = await make_auth(); b = await make_auth()
    m = await create_memory(db_session, owner_id=uuid.UUID(a["user_id"]),
                            content="A的私密决策", embedding=_V1)
    assert await get_memory(db_session, m.id, uuid.UUID(b["user_id"])) is None


async def test_list_filter_kind_and_superseded(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    await create_memory(db_session, owner_id=oid, content="决策X", kind="decision", embedding=_V1)
    await create_memory(db_session, owner_id=oid, content="事实Y", kind="fact", embedding=_V2)
    decisions = await list_memories(db_session, oid, kind="decision")
    assert len(decisions) == 1 and decisions[0].content == "决策X"


async def test_find_similar_vector_and_isolation(db_session, make_auth):
    a = await make_auth(); b = await make_auth()
    oa = uuid.UUID(a["user_id"])
    await create_memory(db_session, owner_id=oa, content="预算500万", subject="预算", embedding=_V1)
    await create_memory(db_session, owner_id=oa, content="无关", embedding=_V2)
    # B 用相同向量存一条，绝不应出现在 A 的召回里
    await create_memory(db_session, owner_id=uuid.UUID(b["user_id"]), content="B的记忆", embedding=_V1)

    hits = await find_similar(db_session, owner_id=oa, embedding=_V1, limit=5)
    assert hits[0]["content"] == "预算500万"
    assert all(h["content"] != "B的记忆" for h in hits)


async def test_supersede_excludes_from_recall(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    old = await create_memory(db_session, owner_id=oid, content="预算300万", embedding=_V1)
    new = await create_memory(db_session, owner_id=oid, content="预算500万", embedding=_V1)
    await supersede_memory(db_session, old, new.id)

    refreshed = await get_memory(db_session, old.id, oid)
    assert refreshed.superseded_by == new.id and refreshed.valid_to is not None

    hits = await find_similar(db_session, owner_id=oid, embedding=_V1)
    assert all(h["id"] != old.id for h in hits)


async def test_soft_delete_hides(db_session, make_auth):
    oid = uuid.UUID((await make_auth())["user_id"])
    m = await create_memory(db_session, owner_id=oid, content="临时", embedding=_V1)
    await soft_delete_memory(db_session, m)
    assert await get_memory(db_session, m.id, oid) is None