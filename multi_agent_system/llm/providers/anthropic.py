"""
Anthropic Provider
"""
import aiohttp
import json
from typing import List, Optional
from ..base import LLMProvider, LLMMessage


class AnthropicProvider(LLMProvider):
    """Anthropic API Provider (Claude models)"""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.base_url = kwargs.get("base_url", "https://api.anthropic.com/v1")
        self.anthropic_version = kwargs.get("anthropic_version", "2023-06-01")

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send chat messages to Anthropic API"""
        url = f"{self.base_url}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "Content-Type": "application/json"
        }

        # Separate system message from conversation
        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conversation_messages.append(msg.to_dict())

        payload = {
            "model": self.model,
            "messages": conversation_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature
        }

        if system_message:
            payload["system"] = system_message

        payload.update(kwargs)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Anthropic API error: {resp.status} - {error_text}")

                result = await resp.json()
                return result["content"][0]["text"]

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send completion request to Anthropic API"""
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.chat(messages, temperature, max_tokens, **kwargs)
