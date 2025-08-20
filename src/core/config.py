import threading
from enum import Enum
import json

from provider.ollama import OllamaProvider
from pathlib import Path
from core.prompt import PromptManager
from core.agent.planning_agent import PlanningAgent

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
            self.planning_agent: PlanningAgent = PlanningAgent()
            self.planning_result: str = ""

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

        if self.chat_mode == ChatMode.AGENT and agent_mode == AgentMode.PLANNING:
            prompt: str = self.prompt_manager.get_system_prompt(user_input=user_message)
            planning_prompt: str = self.prompt_manager.planning_prompt
            planning_prompt_structure: str = f"""
WORK SPACE : {self.work_dir}
DIRECTORY STRUCTURE:
{self.planning_agent.get_directory_structure()}
"""
            prompt += planning_prompt + planning_prompt_structure

        try:
            for i in range(3):  # 최대 3번 재시도
                response = self.get_ollama_provider().chat(prompt)

                # PLANNING 모드일 때 특별한 처리
                if self.chat_mode == ChatMode.AGENT and agent_mode == AgentMode.PLANNING:
                    # 1. JSON 포맷인지 확인
                    try:
                        # response가 문자열이라고 가정하고 JSON 파싱 시도
                        json_data = json.loads(response)

                        # 2. PlanningResult 형식인지 확인
                        if self.planning_agent.check_planning_result(json_data):
                            # 3. config의 planning_result에 저장 (JSON 문자열로 저장)
                            self.planning_result = response

                            # 4. JSON을 마크다운으로 변환하여 반환
                            markdown_result = self.planning_agent.format_planning_result_to_markdown(json_data)
                            return markdown_result
                        else:
                            print(f"Invalid PlanningResult format on attempt {i+1}")
                            if i == 2:  # 마지막 시도
                                return f"❌ Failed to get valid PlanningResult format after 3 attempts.\n\nLast response:\n```\n{response}\n```"
                            continue

                    except json.JSONDecodeError:
                        print(f"Invalid JSON format on attempt {i+1}")
                        if i == 2:  # 마지막 시도
                            return f"❌ Failed to get valid JSON format after 3 attempts.\n\nLast response:\n```\n{response}\n```"
                        continue
                else:
                    # 일반 모드일 때는 그대로 반환
                    return response

        except Exception as e:
            raise ValueError(f"Error occurred while chatting: {e}")

        # 이 부분에 도달하면 모든 시도가 실패한 경우
        return "❌ Failed to get a valid response after all attempts."