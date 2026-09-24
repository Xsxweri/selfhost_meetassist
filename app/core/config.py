from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """应用配置，从 .env 文件自动读取"""

    # 应用基础配置
    APP_NAME: str = "Meeting Assistant"
    DEBUG: bool = True

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "meeting_assistant"

    # 由上面的字段拼接出完整的异步数据库 URL
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Ollama / LLM 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:7b"
    EMBEDDING_MODEL: str = "bge-m3"

    # 提示词
    PROMPTS_DIR: str = "prompts"

    # 运行模式：local(本地开发) / hybrid(混合) / cloud(云端)
    RUN_MODE: str = "hybrid"

    # ASR适配层
    ASR_BACKEND: str = "local"  # local / cloud("aliyun" / "tencent")
    WHISPER_MODEL: str = "small"  # tiny, base, small, medium, large
    WHISPER_DEVICE: str = "auto"  # auto / cpu / cuda
    WHISPER_COMPUTE_TYPE: str = "int8"  # 8GB 显存友好
    ASR_LANGUAGE: str | None = None  # 语言，None 表示自动检测
    ASR_SAMPLE_RATE: int = 16000  # 采样率
    ASR_FLUSH_SECONDS: int = 5  # 缓冲满多少秒自动转写一次

    # 云端ASR(占位，hybrid/cloud 模式接入阿里/腾讯/讯飞）
    CLOUD_ASR_PROVIDER: str = ""
    CLOUD_ASR_ENDPOINT: str = ""
    CLOUD_ASR_API_KEY: str = ""

    # JWT 配置（鉴权用）
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis / Celery 异步任务队列
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # 环境变量名严格区分大小写
    )


@lru_cache
def get_settings() -> Settings:
    """
    使用 lru_cache 缓存配置对象，避免每次请求都重新读取 .env 文件。
    FastAPI 依赖注入时直接调用此函数即可。
    """
    return Settings()
