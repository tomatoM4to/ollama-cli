from collections.abc import Iterator

import ollama

from provider.provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "exaone-deep:7.8b"):
        self.model = model
        self.client = ollama.Client(host=base_url)

    def chat_stream(self, message: str) -> Iterator[str]:
        try:
            response_stream = self.client.generate(
                model=self.model,
                prompt=message,
                stream=True
            )

            for chunk in response_stream:
                if hasattr(chunk, 'response') and chunk.response:
                    yield chunk.response

        except ollama.RequestError as e:
            raise ConnectionError(f"Invalid request to Ollama server: {e}") from e
        except ollama.ResponseError as e:
            raise ConnectionError(f"Failed to connect to Ollama server: {e}") from e
