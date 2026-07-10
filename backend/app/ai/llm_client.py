import asyncio
import os
from typing import Optional

import httpx

# 供应商配置表，后续切换只需改环境变量 LLM_PROVIDER + 对应 API_KEY
PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "custom": {
        "base_url": "",
        "api_key_env": "LLM_API_KEY",
        "default_model": "",
    },
}


class LLMClient:
    """统一 LLM 调用封装。OpenAI 兼容协议（Chat Completions）。共享 httpx 连接池。"""

    _shared_client: httpx.AsyncClient | None = None
    _client_lock = asyncio.Lock()

    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", "deepseek")
        cfg = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["deepseek"])
        self._base_url = os.getenv("LLM_BASE_URL", cfg["base_url"])
        self._api_key = os.getenv(cfg["api_key_env"], os.getenv("LLM_API_KEY", ""))
        self._model = os.getenv("LLM_MODEL", cfg["default_model"])
        self._timeout = int(os.getenv("LLM_TIMEOUT", "60"))

    @classmethod
    async def _get_client(cls, timeout: int = 60) -> httpx.AsyncClient:
        if cls._shared_client is None:
            async with cls._client_lock:
                if cls._shared_client is None:
                    cls._shared_client = httpx.AsyncClient(timeout=timeout)
        return cls._shared_client

    @classmethod
    async def close_shared_client(cls) -> None:
        if cls._shared_client is not None:
            await cls._shared_client.aclose()
            cls._shared_client = None

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """单次非流式调用。返回完整响应（含 tool_calls 列表）。"""
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        client = await self._get_client(self._timeout)
        resp = await client.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    async def chat_stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        """流式调用生成器。逐条 yield delta。"""
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        client = await self._get_client(self._timeout)
        async with client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    import json
                    yield json.loads(line[6:])
