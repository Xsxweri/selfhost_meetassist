import httpx
from app.core.config import get_settings

settings = get_settings()


async def chat(prompt: str, system: str | None = None, json_mode: bool = False) -> str:
    """调用 Ollama chat；json_mode=True 时强制模型输出 JSON（qwen2.5 支持 format=json）"""
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload: dict = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.0},
    }
    if json_mode:
        payload["format"] = "json"
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]