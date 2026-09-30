from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 生产环境禁止使用的弱密钥占位值
_INSECURE_SECRETS = {"your-secret-key-change-in-production", "", "change-me", "secret", "changeme"}


class Settings(BaseSettings):
    """应用配置，从 .env 文件自动读取"""

    # 应用基础配置
    APP_NAME: str = "Meeting Assistant"
    DEBUG: bool = True
    SQL_ECHO: bool = False  #SQL 回显开关，与 DEBUG 解耦；生产保持 False
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"  # 逗号分隔白名单

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
    WHISPER_COMPUTE_TYPE: str = "int8"  # 显存友好
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

    # 记忆层
    CHECKPOINT_BACKEND: str = "memory"  # memory | postgres
    MEMORY_ENABLED: bool = True
    MEMORY_TOP_K: int = 6  # 召回条数
    MEMORY_SIM_THRESHOLD: float = 0.82  # 抽取去重阈值（超过视为同一事实→演进）
    MEMORY_RECALL_MIN_SIM: float = 0.65  # 召回相似度下限
    MEMORY_HYBRID: bool = True  # 向量 + 关键词(trgm) 混合
    THREAD_SUMMARY_THRESHOLD: int = 12  # 会话超过该轮数触发滚动摘要

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # 环境变量名严格区分大小写
    )

    @model_validator(mode="after")
    def check_insecure_settings(self):
        if not self.DEBUG and self.SECRET_KEY.strip() in _INSECURE_SECRETS:
            raise ValueError(
                "生产环境(DEBUG=False)必须配置强随机 SECRET_KEY，禁止使用默认占位值"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """
    使用 lru_cache 缓存配置对象，避免每次请求都重新读取 .env 文件。
    FastAPI 依赖注入时直接调用此函数即可。
    """
    return Settings()
