from collections.abc import Iterator

import anthropic
from ollie.provider.provider import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def chat_stream(self, message: str, **kwargs) -> Iterator[str]:
        with self.client.messages.stream(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", 1000),
            messages=[{"role": "user", "content": message}],
        ) as stream:
            yield from stream.text_stream
