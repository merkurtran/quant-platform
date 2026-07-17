import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from anthropic import AsyncAnthropic

from app.core.config import get_settings

PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    "claude": {
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-sonnet-4-20250514",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "anthropic_base_url": "https://api.deepseek.com/anthropic",
        "default_model": "deepseek-chat",
    },
    "custom": {
        "base_url": "",
        "default_model": "",
    },
}


class LLMConfigurationError(RuntimeError):
    pass


class LLMClient:
    """Provider-aware LLM client that preserves the existing OpenAI response shape."""

    _shared_client: httpx.AsyncClient | None = None
    _client_lock = asyncio.Lock()

    def __init__(self):
        settings = get_settings()
        self._provider = settings.llm.provider.strip().lower()
        cfg = PROVIDER_CONFIG.get(self._provider, PROVIDER_CONFIG["custom"])
        self._base_url = cfg["base_url"]
        self._api_key = settings.llm.api_key.get_secret_value().strip()
        self._model = settings.llm.model
        self._timeout = 60

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    def _require_api_key(self) -> None:
        if not self._api_key:
            raise LLMConfigurationError("请在 .env 中配置 LLM__API_KEY 后使用 AI 功能")

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
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        self._require_api_key()
        if self._provider == "claude":
            return await self._chat_claude(messages, tools, temperature, max_tokens)
        return await self._chat_openai_compatible(
            messages, tools, temperature, max_tokens
        )

    async def _chat_openai_compatible(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not self._base_url:
            raise LLMConfigurationError("当前 LLM provider 未配置可用的 API 地址")

        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        client = await self._get_client(self._timeout)
        response = await client.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        return response.json()

    async def _chat_claude(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        system, claude_messages = self._to_claude_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": claude_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [self._to_claude_tool(tool) for tool in tools]

        response = await self._anthropic_client().messages.create(**kwargs)
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input, ensure_ascii=False),
                        },
                    }
                )

        message: dict[str, Any] = {
            "role": "assistant",
            "content": "\n".join(text_parts),
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls" if tool_calls else "stop",
                    "message": message,
                }
            ]
        }

    async def web_search(self, system: str, prompt: str, max_uses: int = 5) -> str:
        """Run Claude server-side web search and return the final text response."""
        self._require_api_key()
        if self._provider not in {"claude", "deepseek"}:
            raise LLMConfigurationError(
                "当前 LLM provider 不支持项目内置联网搜索，请使用 claude 或 deepseek"
            )

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        response = None
        for _ in range(3):
            response = await self._web_search_client().messages.create(
                model=self._model,
                system=system,
                messages=messages,
                max_tokens=4096,
                temperature=0.1,
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": max_uses,
                    }
                ],
            )
            if response.stop_reason != "pause_turn":
                break
            messages.append(
                {
                    "role": "assistant",
                    "content": [block.model_dump() for block in response.content],
                }
            )

        if response is None:
            return ""
        return "\n".join(
            block.text for block in response.content if block.type == "text"
        )

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict[str, Any]]:
        self._require_api_key()
        if self._provider == "claude":
            yield await self.chat(messages, tools, temperature, max_tokens)
            return

        body: dict[str, Any] = {
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
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    yield json.loads(line[6:])

    def _anthropic_client(self) -> AsyncAnthropic:
        return AsyncAnthropic(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout,
        )

    def _web_search_client(self) -> AsyncAnthropic:
        if self._provider == "deepseek":
            base_url = PROVIDER_CONFIG["deepseek"]["anthropic_base_url"]
        else:
            base_url = self._base_url
        return AsyncAnthropic(
            api_key=self._api_key,
            base_url=base_url,
            timeout=self._timeout,
        )

    @staticmethod
    def _to_claude_tool(tool: dict[str, Any]) -> dict[str, Any]:
        function = tool["function"]
        return {
            "name": function["name"],
            "description": function.get("description", ""),
            "input_schema": function.get("parameters", {"type": "object"}),
        }

    @staticmethod
    def _to_claude_messages(
        messages: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        system_parts: list[str] = []
        result: list[dict[str, Any]] = []
        for message in messages:
            role = message["role"]
            if role == "system":
                system_parts.append(str(message.get("content", "")))
                continue
            if role == "tool":
                result.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message["tool_call_id"],
                                "content": str(message.get("content", "")),
                            }
                        ],
                    }
                )
                continue

            content: Any = message.get("content", "")
            if role == "assistant" and message.get("tool_calls"):
                blocks: list[dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": str(content)})
                for call in message["tool_calls"]:
                    arguments = call["function"].get("arguments", "{}")
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call["id"],
                            "name": call["function"]["name"],
                            "input": json.loads(arguments),
                        }
                    )
                content = blocks
            result.append({"role": role, "content": content})
        return "\n\n".join(system_parts), result
