import threading
from enum import Enum

from provider.ollama import OllamaProvider
from pathlib import Path
from core.prompt import PromptManager

class ChatMode(Enum):
    ASK = 'ask'
    AGENT = 'agent'

class AgentMode(Enum):
    PLANNING = 'planning'
    READER = 'reader'
    WRITER = 'writer'
    REVIEWER = 'reviewer'

class Config:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self.stream = False
            self.platform: str | None = None
            self.model: str | None = None
            self.chat_mode: ChatMode = ChatMode.ASK
            self.ollama_provider: OllamaProvider | None = None
            self.work_dir: Path | None = None
            self.prompt_manager: PromptManager = PromptManager()
            self.agent_mode: AgentMode = AgentMode.PLANNING
    def initialize(
            self,
            platform: str,
            model: str,
            work_dir: Path,
            base_url: str = "http://localhost:11434"
    ) -> None:
        self.platform = platform
        self.model = model
        self.work_dir = work_dir
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
        if self.model is None:
            raise ValueError("Model is not set. Please initialize the configuration first.")
        return self.model

    def get_ollama_provider(self) -> OllamaProvider:
        if self.ollama_provider is None:
            raise ValueError("Ollama provider is not set. Please initialize the configuration first.")
        return self.ollama_provider

    def chat(self, user_message: str, agent_mode: AgentMode | None = None) -> str:
        if self.ollama_provider is None:
            raise ValueError("Ollama provider is not set. Please initialize the configuration first.")

        if self.chat_mode == ChatMode.ASK:
            prompt = self.prompt_manager.get_ask_prompt(user_message)
        elif self.chat_mode == ChatMode.AGENT:
            prompt = self.prompt_manager.get_system_prompt(user_input=user_message)
        try:
            response = self.get_ollama_provider().chat(prompt)
            return response
        except Exception as e:
            raise ValueError(f"Error occurred while chatting: {e}")