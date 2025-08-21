from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    @abstractmethod
    def chat_stream(self, message: str, **kwargs) -> Iterator[str]:
        pass


class MultiLLMClient:
    def __init__(self):
        self.providers: dict[str, LLMProvider] = {}

    def add_provider(self, name: str, provider: LLMProvider):
        self.providers[name] = provider

    def chat_stream(self, provider_name: str, message: str, **kwargs) -> Iterator[str]:
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")

        return self.providers[provider_name].chat_stream(message, **kwargs)
