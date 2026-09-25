import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _pg_dsn() -> str:
    return (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


async def make_checkpointer():
    """构建 LangGraph checkpointer，返回 (checkpointer, cleanup)。

    - memory（默认）：InMemorySaver，单进程有效，无额外依赖
    - postgres：AsyncPostgresSaver + 连接池，跨重启/多 worker 持久；
      需先 `uv add langgraph-checkpoint-postgres "psycopg[binary,pool]"`
      初始化失败自动降级为 memory，绝不阻断启动。
    """
    backend = (settings.CHECKPOINT_BACKEND or "memory").lower()
    if backend == "postgres":
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: F401
            from psycopg_pool import AsyncConnectionPool  # noqa: F401

            pool = AsyncConnectionPool(
                conninfo=_pg_dsn(), max_size=10, open=False,
                kwargs={"autocommit": True, "prepare_threshold": 0},
            )
            await pool.open()
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            logger.info("checkpointer=postgres ready")

            async def _cleanup():
                await pool.close()

            return saver, _cleanup
        except Exception as e:  # noqa: BLE001 - 缺依赖/连不上则降级
            logger.warning("postgres checkpointer init failed, fallback to memory: %s", e)

    from langgraph.checkpoint.memory import InMemorySaver
    return InMemorySaver(), None