"""
LLM Manager - Multi-provider orchestration with fallback
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from .base import LLMProvider, LLMMessage


logger = logging.getLogger(__name__)


class LLMManager:
    """Manages multiple LLM providers with automatic fallback"""

    def __init__(self, retry_count: int = 3, fallback_enabled: bool = True):
        self.providers: Dict[str, LLMProvider] = {}
        self.provider_priorities: Dict[str, int] = {}
        self.default_provider: Optional[str] = None
        self.retry_count = retry_count
        self.fallback_enabled = fallback_enabled
        self.stats: Dict[str, Dict[str, int]] = {}

    def register_provider(
        self,
        name: str,
        provider: LLMProvider,
        priority: int = 100,
        set_as_default: bool = False
    ):
        """
        Register a new LLM provider

        Args:
            name: Provider identifier (e.g., "openai", "anthropic")
            provider: LLMProvider instance
            priority: Priority for fallback (lower = higher priority)
            set_as_default: Set this provider as default
        """
        self.providers[name] = provider
        self.provider_priorities[name] = priority
        self.stats[name] = {"success": 0, "failures": 0, "total": 0}

        if set_as_default or self.default_provider is None:
            self.default_provider = name

        logger.info(f"Registered provider: {name} (priority: {priority})")

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get provider by name"""
        return self.providers.get(name)

    def get_sorted_providers(self) -> List[str]:
        """Get providers sorted by priority"""
        return sorted(
            self.providers.keys(),
            key=lambda x: self.provider_priorities.get(x, 999)
        )

    async def chat(
        self,
        messages: List[LLMMessage],
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat messages with automatic fallback

        Args:
            messages: List of LLMMessage objects
            provider: Specific provider to use (None = use default + fallback)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict with 'response', 'provider', and 'success' keys
        """
        if provider:
            # Use specific provider only
            return await self._call_provider(
                provider, messages, temperature, max_tokens, **kwargs
            )

        # Try default provider first, then fallback
        providers_to_try = [self.default_provider] if self.default_provider else []

        if self.fallback_enabled:
            # Add other providers in priority order
            for p in self.get_sorted_providers():
                if p not in providers_to_try:
                    providers_to_try.append(p)

        last_error = None

        for provider_name in providers_to_try:
            try:
                result = await self._call_provider(
                    provider_name, messages, temperature, max_tokens, **kwargs
                )
                if result["success"]:
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue

        # All providers failed
        raise Exception(f"All providers failed. Last error: {last_error}")

    async def _call_provider(
        self,
        provider_name: str,
        messages: List[LLMMessage],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Call a specific provider with retry logic"""
        provider = self.providers.get(provider_name)

        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")

        self.stats[provider_name]["total"] += 1
        last_error = None

        for attempt in range(self.retry_count):
            try:
                response = await provider.chat(
                    messages, temperature, max_tokens, **kwargs
                )
                self.stats[provider_name]["success"] += 1
                logger.info(f"Provider {provider_name} succeeded (attempt {attempt + 1})")

                return {
                    "response": response,
                    "provider": provider_name,
                    "success": True,
                    "attempt": attempt + 1
                }

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Provider {provider_name} failed (attempt {attempt + 1}/{self.retry_count}): {e}"
                )

                if attempt < self.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # All retries failed
        self.stats[provider_name]["failures"] += 1
        raise Exception(f"Provider {provider_name} failed after {self.retry_count} attempts: {last_error}")

    async def complete(
        self,
        prompt: str,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send completion request with automatic fallback

        Args:
            prompt: Input prompt text
            provider: Specific provider to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters

        Returns:
            Dict with 'response', 'provider', and 'success' keys
        """
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.chat(messages, provider, temperature, max_tokens, **kwargs)

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Get usage statistics for all providers"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset usage statistics"""
        for provider in self.stats:
            self.stats[provider] = {"success": 0, "failures": 0, "total": 0}

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about registered providers"""
        return {
            "providers": list(self.providers.keys()),
            "default_provider": self.default_provider,
            "priorities": self.provider_priorities.copy(),
            "stats": self.get_stats()
        }
