from functools import lru_cache
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()


def _prompts_dir() -> Path:
    p = Path(settings.PROMPTS_DIR)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    return p


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """按名加载提示词文件（<name>.md），带缓存"""
    path = _prompts_dir() / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **kwargs) -> str:
    """加载并渲染提示词：仅替换 {{key}} 占位符，不影响 JSON 花括号"""
    text = load_prompt(name)
    for key, value in kwargs.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def reload_prompts() -> None:
    """清空缓存（开发时热更新提示词用）"""
    load_prompt.cache_clear()
