from pathlib import Path


class ReaderAgent:
    def __init__(self, work_dir: Path | None = None):
        self.work_dir = work_dir

    def set_work_dir(self, work_dir: Path) -> None:
        """작업 디렉토리를 설정."""
        self.work_dir = work_dir

    def read_file(self, file_path: str) -> str:
        """파일을 읽는 기본 메서드 (호환성 유지)"""
        with open(file_path, encoding='utf-8') as file:
            return file.read()

    def read_file_safely(self, file_path: str) -> tuple[bool, str]:
        """
        파일을 안전하게 읽는 메서드

        Returns:
            tuple[bool, str]: (성공 여부, 파일 내용 또는 에러 메시지)
        """
        try:
            # work_dir 확인
            if self.work_dir is None:
                return False, "Work directory is not set. Please set work directory first."

            # 절대 경로로 변환
            if not Path(file_path).is_absolute():
                full_path = self.work_dir / file_path
            else:
                full_path = Path(file_path)

            if not full_path.exists():
                return False, f"File not found: {file_path}"

            if not full_path.is_file():
                return False, f"Path is not a file: {file_path}"

            with open(full_path, encoding='utf-8') as f:
                content = f.read()

            return True, content

        except PermissionError:
            return False, f"Permission denied: {file_path}"
        except UnicodeDecodeError:
            return False, f"Cannot decode file (binary file?): {file_path}"
        except Exception as e:
            return False, f"Error reading file {file_path}: {str(e)}"

    def create_file_safely(self, file_path: str, content: str = "") -> tuple[bool, str]:
        """
        파일을 안전하게 생성하는 메서드

        Returns:
            tuple[bool, str]: (성공 여부, 성공/에러 메시지)
        """
        try:
            # work_dir 확인
            if self.work_dir is None:
                return False, "Work directory is not set. Please set work directory first."

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

    def read_planning_files(self, planning_data: dict) -> str:
        """
        Planning 결과에서 읽어야 할 파일들을 읽고 프롬프트 형식으로 반환

        Args:
            planning_data: Planning 결과 딕셔너리

        Returns:
            str: "파일명: 파일내용" 형식의 문자열
        """
        files_to_read = planning_data.get('files_to_read', [])

        if not files_to_read:
            return "No files to read according to planning result."

        result_parts = []
        successful_reads = 0

        for file_path in files_to_read:
            success, content = self.read_file_safely(file_path)

            if success:
                result_parts.append(f"{file_path}:\n{content}")
                successful_reads += 1
            else:
                result_parts.append(f"{file_path}:\n[ERROR] {content}")

        header = f"📖 Read {successful_reads}/{len(files_to_read)} files successfully\n\n"
        return header + "\n\n---\n\n".join(result_parts)

    def create_planning_files(self, planning_data: dict) -> str:
        """
        Planning 결과에서 생성해야 할 파일들을 생성

        Args:
            planning_data: Planning 결과 딕셔너리

        Returns:
            str: 생성 결과 메시지
        """
        files_to_create = planning_data.get('files_to_create', [])

        if not files_to_create:
            return "No files to create according to planning result."

        result_parts = []
        successful_creates = 0

        for file_path in files_to_create:
            success, message = self.create_file_safely(file_path)

            if success:
                successful_creates += 1
                result_parts.append(f"✅ {message}")
            else:
                result_parts.append(f"❌ {message}")

        header = f"📝 Created {successful_creates}/{len(files_to_create)} files successfully\n\n"
        return header + "\n".join(result_parts)

    def get_planning_summary(self, planning_data: dict) -> str:
        """
        Planning 결과의 요약 정보를 반환

        Args:
            planning_data: Planning 결과 딕셔너리

        Returns:
            str: Planning 요약 정보
        """
        summary = "📋 Planning Summary:\n\n"
        summary += f"📖 Files to read: {len(planning_data.get('files_to_read', []))}\n"
        summary += f"✨ Files to create: {len(planning_data.get('files_to_create', []))}\n"
        summary += f"✏️ Files to modify: {len(planning_data.get('files_to_modify', []))}\n"
        summary += f"📦 Dependencies: {len(planning_data.get('dependencies_required', []))}\n"

        return summary

    def execute_planning_workflow(self, planning_data: dict) -> str:
        """
        Planning 결과를 바탕으로 전체 워크플로우를 실행

        Args:
            planning_data: Planning 결과 딕셔너리

        Returns:
            str: 실행 결과 종합 리포트
        """
        try:
            results = []

            # 1. 요약 정보
            results.append(self.get_planning_summary(planning_data))

            # 2. 파일 생성
            results.append("## 🔧 File Creation")
            results.append(self.create_planning_files(planning_data))

            # 3. 파일 읽기
            results.append("## 📚 File Reading")
            results.append(self.read_planning_files(planning_data))

            return "\n\n".join(results)

        except Exception as e:
            return f"❌ Error executing planning workflow: {str(e)}"

    def get_reading_prompt(self, planning_data: dict) -> str:
        """
        Reading 모드를 위한 프롬프트를 생성

        Args:
            planning_data: Planning 결과 딕셔너리

        Returns:
            str: Reading context 프롬프트
        """
        try:
            file_contents = self.read_planning_files(planning_data)
            reading_prompt = f"""
READING CONTEXT FROM PLANNING:
{file_contents}

Please analyze the above files and provide insights based on the user's request.
"""
            return reading_prompt
        except Exception as e:
            return f"\n\n[WARNING] Could not read planning files: {str(e)}"

