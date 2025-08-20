from pathlib import Path
from typing import Literal, TypedDict


class FileDict(TypedDict):
    path: str
    action: Literal["create", "modify", "delete"]
    content: str


class ResponseDict(TypedDict):
    files: list[FileDict]
    summary: str


class WriterAgent:
    def __init__(self, work_dir: Path | None = None, strict_security: bool = True):
        self.work_dir = work_dir
        self.strict_security = strict_security  # 보안 모드 활성화

    def set_work_dir(self, work_dir: Path) -> None:
        """작업 디렉토리를 설정합니다."""
        self.work_dir = work_dir

    def set_security_mode(self, strict: bool) -> None:
        """보안 모드를 설정합니다."""
        self.strict_security = strict

    def _validate_file_path_security(self, file_path: str) -> tuple[bool, str]:
        """
        파일 경로의 보안을 검증하는 메서드

        Args:
            file_path: 검증할 파일 경로

        Returns:
            tuple[bool, str]: (안전 여부, 에러 메시지 또는 정규화된 경로)
        """
        if self.work_dir is None:
            return False, "Work directory is not set. Please set work directory first."

        try:
            # 절대 경로로 변환
            if not Path(file_path).is_absolute():
                full_path = self.work_dir / file_path
            else:
                full_path = Path(file_path)

            # 경로 정규화 (../ 등의 상대 경로 해결)
            normalized_path = full_path.resolve()
            work_dir_resolved = self.work_dir.resolve()

            # 보안 모드가 활성화된 경우 work_dir 내부인지 확인
            if self.strict_security:
                try:
                    # work_dir의 하위 디렉토리인지 확인
                    normalized_path.relative_to(work_dir_resolved)
                except ValueError:
                    return False, f"🚫 Security violation: Access denied to path outside work directory.\nAttempted: {normalized_path}\nAllowed: {work_dir_resolved} and subdirectories"

            # 민감한 시스템 파일들 체크
            dangerous_patterns = [
                '/etc/',
                '/bin/',
                '/usr/bin/',
                '/sbin/',
                '/usr/sbin/',
                'C:\\Windows\\',
                'C:\\Program Files\\',
                'C:\\Program Files (x86)\\',
                '/System/',
                '/Library/',
                '/.ssh/',
                '/.aws/',
                '/.config/',
            ]

            path_str = str(normalized_path)
            for pattern in dangerous_patterns:
                if pattern in path_str:
                    return False, f"🚫 Security violation: Access denied to system directory: {pattern}"

            # 숨김 파일이나 중요한 설정 파일들 체크
            dangerous_files = [
                '.env',
                '.secret',
                '.key',
                'id_rsa',
                'id_dsa',
                'id_ecdsa',
                'id_ed25519',
                'passwd',
                'shadow',
                'hosts',
            ]

            file_name = normalized_path.name.lower()
            for dangerous_file in dangerous_files:
                if dangerous_file in file_name:
                    return False, f"🚫 Security violation: Access denied to sensitive file: {dangerous_file}"

            return True, str(normalized_path)

        except Exception as e:
            return False, f"🚫 Security validation error: {str(e)}"

    def _process_file_content(self, content: str) -> str:
        """
        JSON에서 온 파일 내용을 실제 파일 형식으로 변환

        Args:
            content: JSON에서 파싱된 파일 내용 (이미 일부 이스케이프 해제됨)

        Returns:
            str: 실제 파일에 쓸 내용
        """
        # JSON 파싱 과정에서 \\n은 이미 \n으로, \\"는 이미 "로 변환됨
        # 따라서 추가 처리가 필요하지 않을 수도 있지만,
        # 혹시 모를 케이스를 위해 체크
        return content

    def check_writer_result(self, data: dict) -> bool:
        """
        WriterResult 형식이 맞는지 확인하는 메서드

        Args:
            data: 검증할 딕셔너리 데이터

        Returns:
            bool: WriterResult 형식이 맞으면 True, 아니면 False
        """
        required_keys = ['files', 'summary']

        # 모든 필수 키가 있는지 확인
        if not all(key in data for key in required_keys):
            return False

        # summary 타입 검증
        if not isinstance(data['summary'], str):
            return False

        # files 타입 검증
        if not isinstance(data['files'], list):
            return False

        # 각 파일 객체 검증
        for file_obj in data['files']:
            if not isinstance(file_obj, dict):
                return False

            # 파일 객체 필수 키 확인
            file_required_keys = ['path', 'action', 'content']
            if not all(key in file_obj for key in file_required_keys):
                return False

            # 타입 검증
            if not isinstance(file_obj['path'], str):
                return False
            if not isinstance(file_obj['action'], str):
                return False
            if not isinstance(file_obj['content'], str):
                return False

            # action 값 검증
            valid_actions = ['create', 'modify', 'delete']
            if file_obj['action'] not in valid_actions:
                return False

        return True

    def write_file_safely(self, file_path: str, content: str, action: str = "create") -> tuple[bool, str]:
        """
        파일을 안전하게 작성하는 메서드

        Args:
            file_path: 파일 경로
            content: 파일 내용 (JSON에서 온 이스케이프된 문자열)
            action: 액션 타입 (create, modify, delete)

        Returns:
            tuple[bool, str]: (성공 여부, 성공/에러 메시지)
        """
        try:
            # 보안 검증 먼저 수행
            is_safe, validated_path_or_error = self._validate_file_path_security(file_path)
            if not is_safe:
                return False, validated_path_or_error

            full_path = Path(validated_path_or_error)

            if action == "delete":
                if full_path.exists():
                    full_path.unlink()
                    return True, f"File deleted successfully: {file_path}"
                else:
                    return False, f"File not found for deletion: {file_path}"

            elif action in ["create", "modify"]:
                # 디렉토리가 없으면 생성
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # modify의 경우 파일이 존재해야 함
                if action == "modify" and not full_path.exists():
                    return False, f"File not found for modification: {file_path}"

                # create의 경우 파일이 이미 존재하면 modify로 처리
                if action == "create" and full_path.exists():
                    action = "modify"

                # 파일 작성 - JSON에서 온 이스케이프된 내용 처리
                processed_content = self._process_file_content(content)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)

                return True, f"File {action}d successfully: {file_path}"

            else:
                return False, f"Invalid action: {action}"

        except PermissionError:
            return False, f"Permission denied: {file_path}"
        except Exception as e:
            return False, f"Error writing file {file_path}: {str(e)}"

    def execute_writer_result(self, writer_data: dict) -> str:
        """
        Writer 결과를 실행하여 파일들을 작성

        Args:
            writer_data: Writer 결과 딕셔너리

        Returns:
            str: 실행 결과 메시지
        """
        files = writer_data.get('files', [])
        summary = writer_data.get('summary', '')

        if not files:
            return "No files to write according to writer result."

        result_parts = []
        successful_writes = 0

        for file_obj in files:
            file_path = file_obj.get('path', '')
            action = file_obj.get('action', 'create')
            content = file_obj.get('content', '')

            success, message = self.write_file_safely(file_path, content, action)

            if success:
                successful_writes += 1
                result_parts.append(f"✅ {message}")
            else:
                result_parts.append(f"❌ {message}")

        header = f"📝 Writer executed {successful_writes}/{len(files)} file operations successfully\n\n"
        summary_section = f"Summary: {summary}\n\n" if summary else ""

        return header + summary_section + "\n".join(result_parts)

    def format_writer_result_to_markdown(self, data: dict) -> str:
        """
        WriterResult를 마크다운 형식으로 변환하는 메서드

        Args:
            data: WriterResult 딕셔너리

        Returns:
            str: 마크다운 형식의 문자열
        """
        markdown = "# 📝 Writer Result\n\n"

        # Summary 섹션
        summary = data.get('summary', '')
        if summary:
            markdown += "## 📋 Summary\n"
            markdown += f"{summary}\n\n"

        # Files 섹션
        files = data.get('files', [])
        markdown += "## 📄 File Operations\n"

        if files:
            for _i, file_obj in enumerate(files, 1):
                path = file_obj.get('path', 'Unknown path')
                action = file_obj.get('action', 'unknown')
                content = file_obj.get('content', '')

                # 액션에 따른 이모지
                action_emoji = {
                    'create': '✨',
                    'modify': '✏️',
                    'delete': '🗑️'
                }.get(action, '📄')

                markdown += f"### {action_emoji} {action.title()}: `{path}`\n"

                if action != 'delete' and content:
                    # 코드 블록으로 내용 표시 (처음 10줄만)
                    content_lines = content.split('\n')
                    if len(content_lines) > 10:
                        preview_content = '\n'.join(content_lines[:10]) + '\n...'
                    else:
                        preview_content = content

                    # 파일 확장자에 따른 언어 감지
                    file_ext = Path(path).suffix.lower()
                    language = {
                        '.py': 'python',
                        '.js': 'javascript',
                        '.ts': 'typescript',
                        '.html': 'html',
                        '.css': 'css',
                        '.json': 'json',
                        '.md': 'markdown',
                        '.yml': 'yaml',
                        '.yaml': 'yaml'
                    }.get(file_ext, '')

                    markdown += f"```{language}\n{preview_content}\n```\n"

                markdown += "\n"
        else:
            markdown += "- No file operations specified\n"

        return markdown
