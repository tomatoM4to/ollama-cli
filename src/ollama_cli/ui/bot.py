from collections.abc import Iterator

from ollama_cli.ui.callbacks import ChatCallback, ChatEvent
from provider.ollama import OllamaProvider


class OllamaBot:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "exaone-deep:7.8b") -> None:
        self.callbacks: list[ChatCallback] = []
        self.provider = OllamaProvider(base_url=base_url, model=model)

    def add_callback(self, callback: ChatCallback) -> None:
        self.callbacks.append(callback)

    def notify_callbacks(self, event: ChatEvent, message: str) -> None:
        for callback in self.callbacks:
            callback.on_event(event, message)

    def process_message_stream(self, message: str) -> Iterator[str]:
        try:
            self.notify_callbacks(ChatEvent.START_PROCESSING, "Starting to process message with Ollama")

            for chunk in self.provider.chat_stream(message):
                if chunk.strip():
                    yield chunk

        except Exception as e:
            error_message = f"Ollama error occurred: {str(e)}"
            self.notify_callbacks(ChatEvent.ERROR, error_message)
            yield "I apologize, but I encountered an error while processing your message with Ollama."

    def process_message(self, message: str) -> str:
        try:
            self.notify_callbacks(ChatEvent.START_PROCESSING, "Starting to process message with Ollama")

            response_parts = []
            for chunk in self.provider.chat_stream(message):
                if chunk.strip():
                    response_parts.append(chunk)

            complete_response = ''.join(response_parts)
            self.notify_callbacks(ChatEvent.PROCESSING_COMPLETE, "Response generation complete")
            return complete_response

        except Exception as e:
            error_message = f"Ollama error occurred: {str(e)}"
            self.notify_callbacks(ChatEvent.ERROR, error_message)
            return "I apologize, but I encountered an error while processing your message with Ollama."
