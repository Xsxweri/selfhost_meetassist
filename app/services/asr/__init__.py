from app.core.config import get_settings
from app.services.asr.base import BaseASR
from app.services.asr.cloud_asr import CloudASR
from app.services.asr.local_asr import LocalASR

settings = get_settings()
_asr_instance: BaseASR | None = None

def get_asr() -> BaseASR:
    """按运行模式/后端配置返回 ASR 单例，业务层不感知具体实现"""
    global _asr_instance
    if _asr_instance is None:
        backend = "cloud" if settings.RUN_MODE == "cloud" else settings.ASR_BACKEND
        _asr_instance = CloudASR() if backend == "cloud" else LocalASR()
    return _asr_instance

__all__ = ["BaseASR", "LocalASR", "CloudASR", "get_asr"]