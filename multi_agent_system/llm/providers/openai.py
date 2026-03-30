"""
OpenAI Provider
"""
import aiohttp
import json
from typing import List, Optional
from ..base import LLMProvider, LLMMessage


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider (GPT models)"""

    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send chat messages to OpenAI API"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                    raise Exception(f"OpenAI API error: {resp.status} - {error_text}")

                result = await resp.json()
                return result["choices"][0]["message"]["content"]

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send completion request to OpenAI API"""
        # Use chat endpoint with single user message
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.chat(messages, temperature, max_tokens, **kwargs)
