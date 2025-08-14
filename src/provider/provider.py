from abc import ABC, abstractmethod
from typing import Iterator
from typing import Optional, Dict

class LLMProvider(ABC):
    @abstractmethod
    def chat_stream(self, message: str, **kwargs) -> Iterator[str]:
        pass

class MultiLLMClient:
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}

    def add_provider(self, name: str, provider: LLMProvider):
        self.providers[name] = provider

    def chat_stream(self, provider_name: str, message: str, **kwargs) -> Iterator[str]:
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")

        return self.providers[provider_name].chat_stream(message, **kwargs)