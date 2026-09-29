"""make_checkpointer：memory 后端正向 + postgres 失败降级路径"""
import pytest
from langgraph.checkpoint.memory import InMemorySaver
import app.agent.checkpoint as ckpt


@pytest.fixture
def backend(monkeypatch):
    def _set(name: str):
        monkeypatch.setattr(ckpt.settings, "CHECKPOINT_BACKEND", name)
    return _set


async def test_memory_backend_returns_inmemory(backend):
    backend("memory")
    saver, cleanup = await ckpt.make_checkpointer()
    assert isinstance(saver, InMemorySaver)
    assert cleanup is None


async def test_empty_backend_defaults_to_memory(backend):
    backend("")  # 空值 → 兜底 memory
    saver, cleanup = await ckpt.make_checkpointer()
    assert isinstance(saver, InMemorySaver)
    assert cleanup is None


async def test_postgres_falls_back_to_memory_on_failure(backend, monkeypatch):
    """依赖缺失或连接失败时必须降级为 memory，绝不抛异常阻断启动"""
    backend("postgres")
    # 指向不可达端口：装了依赖也会 connect 失败 → 触发 except 降级
    monkeypatch.setattr(ckpt, "_pg_dsn", lambda: "postgresql://u:p@127.0.0.1:1/none")
    saver, cleanup = await ckpt.make_checkpointer()
    assert isinstance(saver, InMemorySaver)
    assert cleanup is None