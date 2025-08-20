import json
import threading
from enum import Enum
from pathlib import Path

from core.agent.planning_agent import PlanningAgent
from core.agent.reader_agent import ReaderAgent
from core.agent.writer_agent import WriterAgent
from core.prompt import PromptManager
from provider.ollama import OllamaProvider


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
            self.reader_agent: ReaderAgent = ReaderAgent()
            self.writer_agent: WriterAgent = WriterAgent(strict_security=True)  # 보안 모드 활성화
            self.planning_result: str = ""
            self.writer_result: str = ""

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
        # ReaderAgent에 work_dir 설정
        self.reader_agent.set_work_dir(work_dir)
        # WriterAgent에 work_dir 설정
        self.writer_agent.set_work_dir(work_dir)

    def set_writer_security_mode(self, strict: bool) -> None:
        """WriterAgent의 보안 모드를 설정합니다."""
        self.writer_agent.set_security_mode(strict)

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

            elif agent_mode == AgentMode.READER:
                # READER 모드일 때 planning 결과에서 읽어야 할 파일들을 프롬프트에 포함
                try:
                    planning_data = self._get_planning_data()
                    reading_prompt = self.reader_agent.get_reading_prompt(planning_data)
                    prompt += reading_prompt
                except Exception as e:
                    prompt += f"\n\n[WARNING] Could not read planning files: {str(e)}"

            elif agent_mode == AgentMode.WRITER:
                # WRITER 모드일 때 planning 결과와 읽은 파일 컨텍스트를 포함
                try:
                    planning_data = self._get_planning_data()

                    # Planning에서 지정한 파일들만 수정하도록 제한
                    files_to_modify = planning_data.get('files_to_modify', [])
                    files_to_create = planning_data.get('files_to_create', [])

                    # 읽은 파일 내용 포함
                    file_contents = self.reader_agent.read_planning_files(planning_data)

                    writing_prompt = self.prompt_manager.writing_prompt
                    writer_context = f"""
PLANNING CONTEXT:
Files to modify: {files_to_modify}
Files to create: {files_to_create}

IMPORTANT: Only modify or create the files specified in the planning phase. Do not modify any other files.

{file_contents}

Please generate code that follows the existing patterns and conventions shown in the files above.
"""
                    prompt += writing_prompt + writer_context
                except Exception as e:
                    prompt += f"\n\n[WARNING] Could not prepare writer context: {str(e)}"

            return prompt

        return self.prompt_manager.get_ask_prompt(user_message)

    def _extract_json_from_response(self, response: str) -> str:
        """
        응답에서 JSON 부분만 추출하는 메서드

        Args:
            response: AI 응답 텍스트

        Returns:
            str: 추출된 JSON 문자열
        """
        # 마크다운 코드 블록 제거
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()

        # 첫 번째 { 부터 마지막 } 까지 추출
        start_brace = response.find('{')
        end_brace = response.rfind('}')

        if start_brace != -1 and end_brace != -1 and start_brace < end_brace:
            return response[start_brace:end_brace + 1]

        return response.strip()

    def _process_planning_response(self, response: str, attempt: int) -> tuple[bool, str]:
        """
        Planning 모드 응답을 처리하는 메서드

        Returns:
            tuple[bool, str]: (성공 여부, 결과 또는 에러 메시지)
        """
        try:
            # JSON 부분 추출
            json_response = self._extract_json_from_response(response)
            json_data = json.loads(json_response)

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

    def _process_writer_response(self, response: str, attempt: int) -> tuple[bool, str]:
        """
        Writer 모드 응답을 처리하는 메서드

        Returns:
            tuple[bool, str]: (성공 여부, 결과 또는 에러 메시지)
        """
        try:
            # JSON 부분 추출
            json_response = self._extract_json_from_response(response)
            json_data = json.loads(json_response)

            if self.writer_agent.check_writer_result(json_data):
                self.writer_result = response
                markdown_result = self.writer_agent.format_writer_result_to_markdown(json_data)
                return True, markdown_result
            else:
                print(f"Invalid WriterResult format on attempt {attempt + 1}")
                if attempt == 2:  # 마지막 시도
                    return True, f"❌ Failed to get valid WriterResult format after 3 attempts.\n\nLast response:\n```\n{response}\n```"
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
            # WRITER 모드일 때 특별한 처리
            elif self.chat_mode == ChatMode.AGENT and agent_mode == AgentMode.WRITER:
                success, result = self._process_writer_response(response, attempt)
                if success:
                    return result
                # 실패하면 다음 시도로 계속
                continue
            else:
                # 일반 모드일 때는 그대로 반환
                return response

        # 모든 시도가 실패한 경우
        return "❌ Failed to get a valid response after all attempts."

    def _get_planning_data(self) -> dict:
        """저장된 planning_result JSON을 파싱하여 반환"""
        if not self.planning_result:
            raise ValueError("No planning result available. Please run planning first.")

        try:
            return json.loads(self.planning_result)
        except json.JSONDecodeError:
            raise ValueError("Invalid planning result format. Cannot parse JSON.")

    def _read_file_safely(self, file_path: str) -> tuple[bool, str]:
        return self.reader_agent.read_file_safely(file_path)

    def _create_file_safely(self, file_path: str, content: str = "") -> tuple[bool, str]:
        return self.reader_agent.create_file_safely(file_path, content)

    def read_planning_files(self) -> str:
        planning_data = self._get_planning_data()
        return self.reader_agent.read_planning_files(planning_data)

    def create_planning_files(self) -> str:
        planning_data = self._get_planning_data()
        return self.reader_agent.create_planning_files(planning_data)

    def get_planning_summary(self) -> str:
        planning_data = self._get_planning_data()
        return self.reader_agent.get_planning_summary(planning_data)

    def execute_planning_workflow(self) -> str:
        planning_data = self._get_planning_data()
        return self.reader_agent.execute_planning_workflow(planning_data)

    def _get_writer_data(self) -> dict:
        """저장된 writer_result JSON을 파싱하여 반환"""
        if not self.writer_result:
            raise ValueError("No writer result available. Please run writer first.")

        try:
            return json.loads(self.writer_result)
        except json.JSONDecodeError:
            raise ValueError("Invalid writer result format. Cannot parse JSON.")

    def execute_writer_workflow(self) -> str:
        """Writer 결과를 바탕으로 파일 작성 워크플로우를 실행 (WriterAgent 위임)"""
        writer_data = self._get_writer_data()
        return self.writer_agent.execute_writer_result(writer_data)

    def chat(self, user_message: str, agent_mode: AgentMode | None = None) -> str:
        """메인 채팅 메서드"""
        if self.ollama_provider is None:
            raise ValueError("Ollama provider is not set. Please initialize the configuration first.")

        try:
            prompt = self._build_prompt(user_message, agent_mode)
            return self._execute_chat_with_retry(prompt, agent_mode)
        except Exception as e:
            raise ValueError(f"Error occurred while chatting: {e}")
