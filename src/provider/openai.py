import os
from openai import OpenAI
from provider.provider import LLMProvider
from typing import Iterator

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = 'gpt-4o') -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat_stream(self, message: str, **kwargs) -> Iterator[str]:
        response = self.client.chat.completions.create(
            model=kwargs.get('model', self.model),
            messages=[
                {'role': 'user', 'content': message}
            ],
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
