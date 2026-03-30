"""
OpenRouter Provider
"""
import aiohttp
import json
from typing import List, Optional
from ..base import LLMProvider, LLMMessage


class OpenRouterProvider(LLMProvider):
    """OpenRouter API Provider (Multi-model aggregator)"""

    def __init__(self, api_key: str, model: str = "anthropic/claude-3-sonnet", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.base_url = kwargs.get("base_url", "https://openrouter.ai/api/v1")
        self.app_name = kwargs.get("app_name", "MultiAgentSystem")

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send chat messages to OpenRouter API"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.app_name,
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"OpenRouter API error: {resp.status} - {error_text}")

                result = await resp.json()
                return result["choices"][0]["message"]["content"]

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send completion request to OpenRouter API"""
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.chat(messages, temperature, max_tokens, **kwargs)
