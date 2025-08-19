from collections.abc import Iterator

import ollama

from core.prompt import PromptManager
from provider.provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(
            self,
            model: str,
            base_url: str = "http://localhost:11434",
            auto_detect_mode: bool = True,
            default_mode: str = 'conversation_mode'
    ):
        self.model = model
        self.client = ollama.Client(host=base_url)
        self.prompt_manager = PromptManager()
        self.auto_detect_mode = auto_detect_mode
        self.default_mode = default_mode

    def chat_stream(self, message: str, mode: str | None = None) -> Iterator[str]:
        if mode is None and self.auto_detect_mode:
            mode = self.prompt_manager.detect_response_type(message)
        elif mode is None:
            mode = self.default_mode

        prompt = self.prompt_manager.get_conversation_prompt(
            user_message=message,
            context=None,  # Context can be passed if available
            mode=mode
        )
        try:
            response_stream = self.client.generate(
                model=self.model,
                prompt=prompt,
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

    def chat(self, message: str, mode: str | None = None) -> str:
        if mode is None and self.auto_detect_mode:
            mode = self.prompt_manager.detect_response_type(message)
        elif mode is None:
            mode = self.default_mode

        prompt = self.prompt_manager.get_conversation_prompt(
            user_message=message,
            context=None,  # Context can be passed if available
            mode=mode
        )

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
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