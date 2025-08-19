import threading
from enum import Enum
from provider.ollama import OllamaProvider

class ChatMode(Enum):
    ASK = 'ask'
    AGENT = 'agent'

class Config:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, platform: str, model: str, base_url: str = "http://localhost:11434"):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, platform: str, model: str, base_url: str = "http://localhost:11434"):
        if not self._initialized:
            self._initialized = True
            self.stream = False
            self.platform = platform
            self.model = model
            self.chat_mode: ChatMode = ChatMode.ASK
            self.ollama_provider = OllamaProvider(model=model, base_url=base_url)

    def set_stream(self, stream: bool) -> None:
        self.stream = stream

    def set_chat_mode(self, mode: str):
        if mode in [ChatMode.ASK.value, ChatMode.AGENT.value]:
            self.chat_mode = ChatMode(mode)
        else:
            raise ValueError(f"Invalid chat mode: {mode}. Must be 'ask' or 'agent'")

    def get_stream(self) -> bool:
        return self.stream

    def get_chat_mode(self) -> ChatMode:
        return self.chat_mode

    def get_model(self) -> str:
        return self.model