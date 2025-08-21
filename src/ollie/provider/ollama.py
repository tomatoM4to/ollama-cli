from collections.abc import Iterator

import ollama
from ollie.provider.provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(
            self,
            model: str,
            base_url: str = "http://localhost:11434",
            auto_detect_mode: bool = True,
    ):
        self.model = model
        self.client = ollama.Client(host=base_url)
        self.auto_detect_mode = auto_detect_mode

    def chat_stream(self, message: str) -> Iterator[str]:
        try:
            response_stream = self.client.generate(
                model=self.model,
                prompt=message,
                stream=True,
                think=False,  # Disable thinking time for streaming
            )

            for chunk in response_stream:
                if hasattr(chunk, 'response') and chunk.response:
                    yield chunk.response

        except ollama.RequestError as e:
            raise ConnectionError(f"Invalid request to Ollama server: {e}") from e
        except ollama.ResponseError as e:
            raise ConnectionError(f"Failed to connect to Ollama server: {e}") from e

    def chat(self, message: str) -> str:
        try:
            response = self.client.generate(
                model=self.model,
                prompt=message,
                stream=False,  # Disable streaming for complete response
                think=False,   # Disable thinking time
            )

            # Extract the response text from the response object
            if hasattr(response, 'response'):
                return response.response
            else:
                # Fallback in case the response structure is different
                return str(response)

        except ollama.RequestError as e:
            raise ConnectionError(f"Invalid request to Ollama server: {e}") from e
        except ollama.ResponseError as e:
            raise ConnectionError(f"Failed to connect to Ollama server: {e}") from e
