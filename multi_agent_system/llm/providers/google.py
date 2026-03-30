"""
Google AI Provider
"""
import aiohttp
import json
from typing import List, Optional
from ..base import LLMProvider, LLMMessage


class GoogleProvider(LLMProvider):
    """Google AI API Provider (Gemini models)"""

    def __init__(self, api_key: str, model: str = "gemini-pro", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.base_url = kwargs.get("base_url", "https://generativelanguage.googleapis.com/v1beta")

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send chat messages to Google AI API"""
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json"
        }

        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg.role in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Google AI API error: {resp.status} - {error_text}")

                result = await resp.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send completion request to Google AI API"""
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.chat(messages, temperature, max_tokens, **kwargs)
