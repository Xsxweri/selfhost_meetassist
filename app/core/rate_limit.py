"""全局限流器：按客户端 IP 计数，存储用 Redis（多 worker/多进程共享）"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,       # 按来源IP限流
    storage_uri=settings.REDIS_URL,    # 复用现有Redis，跨进程共享计数
)