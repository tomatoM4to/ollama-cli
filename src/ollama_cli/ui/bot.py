from collections.abc import Iterator

from ollama_cli.core.config import AgentMode, Config
from ollama_cli.ui.callbacks import ChatCallback, ChatEvent


class OllamaBot:
    def __init__(self, config: Config) -> None:
        self.callbacks: list[ChatCallback] = []
        self.config = config

    def add_callback(self, callback: ChatCallback) -> None:
        self.callbacks.append(callback)

    def notify_callbacks(self, event: ChatEvent, message: str) -> None:
        for callback in self.callbacks:
            callback.on_event(event, message)

    def process_message_stream(self, message: str) -> Iterator[str]:
        try:
            for chunk in self.config.get_ollama_provider().chat_stream(message):
                if chunk.strip():
                    yield chunk

        except Exception as e:
            error_message = f"Ollama error occurred: {str(e)}"
            self.notify_callbacks(ChatEvent.ERROR, error_message)
            yield "I apologize, but I encountered an error while processing your message with Ollama."

    def process_message(self, message: str, agent_mode: AgentMode | None = None) -> str:
        try:
            response = self.config.chat(message, agent_mode)
            return response

        except Exception as e:
            error_message = f"Ollama error occurred: {str(e)}"
            self.notify_callbacks(ChatEvent.ERROR, error_message)
            return "I apologize, but I encountered an error while processing your message with Ollama."
