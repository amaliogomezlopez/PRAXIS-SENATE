"""
Base classes for LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Represents a message in a chat conversation"""
    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Send chat messages and get response

        Args:
            messages: List of LLMMessage objects
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific parameters

        Returns:
            Response text from the model
        """
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Send a prompt and get completion

        Args:
            prompt: Input prompt text
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific parameters

        Returns:
            Completion text from the model
        """
        pass

    def get_name(self) -> str:
        """Get provider name"""
        return self.__class__.__name__.replace("Provider", "").lower()
