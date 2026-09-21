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

    # JWT 配置（鉴权用）
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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
