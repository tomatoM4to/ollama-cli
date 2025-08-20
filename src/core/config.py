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

    def _build_prompt(self, user_message: str, agent_mode: AgentMode | None = None) -> str:
        """프롬프트를 생성하는 메서드"""
        if self.chat_mode == ChatMode.ASK:
            return self.prompt_manager.get_ask_prompt(user_message)
        elif self.chat_mode == ChatMode.AGENT:
            prompt = self.prompt_manager.get_system_prompt(user_input=user_message)

            if agent_mode == AgentMode.PLANNING:
                planning_prompt = self.prompt_manager.planning_prompt
                planning_prompt_structure = f"""
WORK SPACE : {self.work_dir}
DIRECTORY STRUCTURE:
{self.planning_agent.get_directory_structure()}
"""
                prompt += planning_prompt + planning_prompt_structure

            return prompt

        return self.prompt_manager.get_ask_prompt(user_message)

    def _process_planning_response(self, response: str, attempt: int) -> tuple[bool, str]:
        """
        Planning 모드 응답을 처리하는 메서드

        Returns:
            tuple[bool, str]: (성공 여부, 결과 또는 에러 메시지)
        """
        try:
            json_data = json.loads(response)

            if self.planning_agent.check_planning_result(json_data):
                self.planning_result = response
                markdown_result = self.planning_agent.format_planning_result_to_markdown(json_data)
                return True, markdown_result
            else:
                print(f"Invalid PlanningResult format on attempt {attempt + 1}")
                if attempt == 2:  # 마지막 시도
                    return True, f"❌ Failed to get valid PlanningResult format after 3 attempts.\n\nLast response:\n```\n{response}\n```"
                return False, ""

        except json.JSONDecodeError:
            print(f"Invalid JSON format on attempt {attempt + 1}")
            if attempt == 2:  # 마지막 시도
                return True, f"❌ Failed to get valid JSON format after 3 attempts.\n\nLast response:\n```\n{response}\n```"
            return False, ""

    def _execute_chat_with_retry(self, prompt: str, agent_mode: AgentMode | None = None, max_retries: int = 3) -> str:
        """
        재시도 로직을 포함한 채팅 실행 메서드
        """
        for attempt in range(max_retries):
            response = self.get_ollama_provider().chat(prompt)

            # PLANNING 모드일 때 특별한 처리
            if self.chat_mode == ChatMode.AGENT and agent_mode == AgentMode.PLANNING:
                success, result = self._process_planning_response(response, attempt)
                if success:
                    return result
                # 실패하면 다음 시도로 계속
                continue
            else:
                # 일반 모드일 때는 그대로 반환
                return response

        # 모든 시도가 실패한 경우
        return "❌ Failed to get a valid response after all attempts."

    def chat(self, user_message: str, agent_mode: AgentMode | None = None) -> str:
        """메인 채팅 메서드"""
        if self.ollama_provider is None:
            raise ValueError("Ollama provider is not set. Please initialize the configuration first.")

        try:
            prompt = self._build_prompt(user_message, agent_mode)
            return self._execute_chat_with_retry(prompt, agent_mode)
        except Exception as e:
            raise ValueError(f"Error occurred while chatting: {e}")