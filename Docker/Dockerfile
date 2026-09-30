# syntax=docker/dockerfile:1
# ---------- builder：装依赖 ----------
FROM python:3.11-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# 先只拷依赖清单，命中层缓存（源码变动不重装依赖）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
# 再拷源码装项目本体
COPY . .
RUN uv sync --frozen --no-dev

# ---------- runtime：精简运行层 ----------
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
COPY --from=builder /app /app
# 非 root 运行
RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
# 启动前先跑迁移，再起 API
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]