import threading
from enum import Enum
import json

from provider.ollama import OllamaProvider
from pathlib import Path
from core.prompt import PromptManager
from core.agent.planning_agent import PlanningAgent
from core.agent.reader_agent import ReaderAgent

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

            elif agent_mode == AgentMode.READER:
                # READER 모드일 때 planning 결과에서 읽어야 할 파일들을 프롬프트에 포함
                try:
                    file_contents = self.read_planning_files()
                    reading_prompt = f"""
READING CONTEXT FROM PLANNING:
{file_contents}

Please analyze the above files and provide insights based on the user's request.
"""
                    prompt += reading_prompt
                except Exception as e:
                    prompt += f"\n\n[WARNING] Could not read planning files: {str(e)}"

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

    def _get_planning_data(self) -> dict:
        """저장된 planning_result JSON을 파싱하여 반환"""
        if not self.planning_result:
            raise ValueError("No planning result available. Please run planning first.")

        try:
            return json.loads(self.planning_result)
        except json.JSONDecodeError:
            raise ValueError("Invalid planning result format. Cannot parse JSON.")

    def _read_file_safely(self, file_path: str) -> tuple[bool, str]:
        """
        파일을 안전하게 읽는 메서드

        Returns:
            tuple[bool, str]: (성공 여부, 파일 내용 또는 에러 메시지)
        """
        try:
            # work_dir 확인
            if self.work_dir is None:
                return False, "Work directory is not set. Please initialize the configuration first."

            # 절대 경로로 변환
            if not Path(file_path).is_absolute():
                full_path = self.work_dir / file_path
            else:
                full_path = Path(file_path)

            if not full_path.exists():
                return False, f"File not found: {file_path}"

            if not full_path.is_file():
                return False, f"Path is not a file: {file_path}"

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return True, content

        except PermissionError:
            return False, f"Permission denied: {file_path}"
        except UnicodeDecodeError:
            return False, f"Cannot decode file (binary file?): {file_path}"
        except Exception as e:
            return False, f"Error reading file {file_path}: {str(e)}"

    def _create_file_safely(self, file_path: str, content: str = "") -> tuple[bool, str]:
        """
        파일을 안전하게 생성하는 메서드

        Returns:
            tuple[bool, str]: (성공 여부, 성공/에러 메시지)
        """
        try:
            # work_dir 확인
            if self.work_dir is None:
                return False, "Work directory is not set. Please initialize the configuration first."

            # 절대 경로로 변환
            if not Path(file_path).is_absolute():
                full_path = self.work_dir / file_path
            else:
                full_path = Path(file_path)

            # 디렉토리가 없으면 생성
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일이 이미 존재하는지 확인
            if full_path.exists():
                return False, f"File already exists: {file_path}"

            # 파일 생성
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, f"File created successfully: {file_path}"

        except PermissionError:
            return False, f"Permission denied: {file_path}"
        except Exception as e:
            return False, f"Error creating file {file_path}: {str(e)}"

    def read_planning_files(self) -> str:
        """
        Planning 결과에서 읽어야 할 파일들을 읽고 프롬프트 형식으로 반환

        Returns:
            str: "파일명: 파일내용" 형식의 문자열
        """
        planning_data = self._get_planning_data()
        files_to_read = planning_data.get('files_to_read', [])

        if not files_to_read:
            return "No files to read according to planning result."

        result_parts = []
        successful_reads = 0

        for file_path in files_to_read:
            success, content = self._read_file_safely(file_path)

            if success:
                result_parts.append(f"{file_path}:\n{content}")
                successful_reads += 1
            else:
                result_parts.append(f"{file_path}:\n[ERROR] {content}")

        header = f"📖 Read {successful_reads}/{len(files_to_read)} files successfully\n\n"
        return header + "\n\n---\n\n".join(result_parts)

    def create_planning_files(self) -> str:
        """
        Planning 결과에서 생성해야 할 파일들을 생성

        Returns:
            str: 생성 결과 메시지
        """
        planning_data = self._get_planning_data()
        files_to_create = planning_data.get('files_to_create', [])

        if not files_to_create:
            return "No files to create according to planning result."

        result_parts = []
        successful_creates = 0

        for file_path in files_to_create:
            success, message = self._create_file_safely(file_path)

            if success:
                successful_creates += 1
                result_parts.append(f"✅ {message}")
            else:
                result_parts.append(f"❌ {message}")

        header = f"📝 Created {successful_creates}/{len(files_to_create)} files successfully\n\n"
        return header + "\n".join(result_parts)

    def get_planning_summary(self) -> str:
        """Planning 결과의 요약 정보를 반환"""
        planning_data = self._get_planning_data()

        summary = "📋 Planning Summary:\n\n"
        summary += f"📖 Files to read: {len(planning_data.get('files_to_read', []))}\n"
        summary += f"✨ Files to create: {len(planning_data.get('files_to_create', []))}\n"
        summary += f"✏️ Files to modify: {len(planning_data.get('files_to_modify', []))}\n"
        summary += f"📦 Dependencies: {len(planning_data.get('dependencies_required', []))}\n"

        return summary

    def execute_planning_workflow(self) -> str:
        """
        Planning 결과를 바탕으로 전체 워크플로우를 실행

        Returns:
            str: 실행 결과 종합 리포트
        """
        try:
            results = []

            # 1. 요약 정보
            results.append(self.get_planning_summary())

            # 2. 파일 생성
            results.append("## 🔧 File Creation")
            results.append(self.create_planning_files())

            # 3. 파일 읽기
            results.append("## 📚 File Reading")
            results.append(self.read_planning_files())

            return "\n\n".join(results)

        except Exception as e:
            return f"❌ Error executing planning workflow: {str(e)}"

    def chat(self, user_message: str, agent_mode: AgentMode | None = None) -> str:
        """메인 채팅 메서드"""
        if self.ollama_provider is None:
            raise ValueError("Ollama provider is not set. Please initialize the configuration first.")

        try:
            prompt = self._build_prompt(user_message, agent_mode)
            return self._execute_chat_with_retry(prompt, agent_mode)
        except Exception as e:
            raise ValueError(f"Error occurred while chatting: {e}")