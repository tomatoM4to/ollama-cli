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
        # JSON 파싱 과정에서 이스케이프는 대부분 해제되지만,
        # 잘못된 이스케이프 시퀀스가 텍스트로 남아있을 수 있음

        processed_content = content

        # 잘못된 이스케이프 시퀀스 처리 (AI가 잘못 생성한 경우)
        if '\\n' in processed_content:
            processed_content = processed_content.replace('\\n', '\n')
        if '\\t' in processed_content:
            processed_content = processed_content.replace('\\t', '\t')
        if '\\"' in processed_content:
            processed_content = processed_content.replace('\\"', '"')
        if '\\\\' in processed_content:
            processed_content = processed_content.replace('\\\\', '\\')

        # 파일별 포매팅 처리는 확장자를 기반으로 write_file_safely에서 처리
        return processed_content

    def _is_css_content(self, content: str) -> bool:
        """CSS 콘텐츠인지 확인"""
        css_indicators = ['{', '}', ':', ';', 'background', 'color', 'font-family', 'margin', 'padding']
        return any(indicator in content for indicator in css_indicators)

    def _is_js_ts_content(self, content: str) -> bool:
        """JavaScript/TypeScript 콘텐츠인지 확인"""
        js_indicators = ['function', 'const', 'let', 'var', '=>', 'console.log', 'document.']
        return any(indicator in content for indicator in js_indicators)

    def _is_python_content(self, content: str) -> bool:
        """Python 콘텐츠인지 확인"""
        py_indicators = ['def ', 'class ', 'import ', 'from ', 'if __name__', 'print(']
        return any(indicator in content for indicator in py_indicators)

    def _is_html_content(self, content: str) -> bool:
        """HTML 콘텐츠인지 확인"""
        html_indicators = ['<html', '<head', '<body', '<div', '<p>', '<!DOCTYPE']
        return any(indicator in content for indicator in html_indicators)

    def _format_css_content(self, content: str) -> str:
        """CSS 콘텐츠 포매팅"""
        # CSS 포매팅 규칙
        lines = []
        current_line = ""
        indent_level = 0

        i = 0
        while i < len(content):
            char = content[i]

            if char == '{':
                current_line += char
                lines.append('    ' * indent_level + current_line.strip())
                current_line = ""
                indent_level += 1
            elif char == '}':
                if current_line.strip():
                    lines.append('    ' * indent_level + current_line.strip())
                indent_level = max(0, indent_level - 1)
                lines.append('    ' * indent_level + '}')
                current_line = ""
                # } 뒤에 공백 라인 추가 (단, 마지막이 아닌 경우)
                if i + 1 < len(content) and content[i + 1:].strip():
                    lines.append("")
            elif char == ';':
                current_line += char
                # 세미콜론 뒤에 공백이나 줄바꿈이 있으면 새 줄로
                if i + 1 < len(content) and content[i + 1] in [' ', '\t', '\n', '\r']:
                    lines.append('    ' * indent_level + current_line.strip())
                    current_line = ""
                    # 세미콜론 뒤의 공백들 건너뛰기
                    j = i + 1
                    while j < len(content) and content[j] in [' ', '\t']:
                        j += 1
                    i = j - 1
                else:
                    # 세미콜론 바로 뒤에 다른 속성이 오는 경우 (압축된 CSS)
                    lines.append('    ' * indent_level + current_line.strip())
                    current_line = ""
            elif char in ['\n', '\r']:
                if current_line.strip():
                    lines.append('    ' * indent_level + current_line.strip())
                    current_line = ""
            elif char == ' ' and not current_line.strip():
                # 앞에 공백만 있는 경우 무시
                pass
            else:
                current_line += char

            i += 1

        # 마지막 라인 처리
        if current_line.strip():
            lines.append('    ' * indent_level + current_line.strip())

        # 빈 줄들 정리 (연속된 빈 줄을 하나로)
        formatted_lines = []
        prev_was_empty = False
        for line in lines:
            if not line.strip():
                if not prev_was_empty:
                    formatted_lines.append("")
                prev_was_empty = True
            else:
                formatted_lines.append(line)
                prev_was_empty = False

        return '\n'.join(formatted_lines)

    def _format_js_ts_content(self, content: str) -> str:
        """JavaScript/TypeScript 콘텐츠 포매팅"""
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue

            # 닫는 괄호들은 들여쓰기 레벨을 먼저 줄임
            if stripped.startswith('}') or stripped.startswith(']') or stripped.startswith(')'):
                indent_level = max(0, indent_level - 1)

            formatted_lines.append('    ' * indent_level + stripped)

            # 여는 괄호들은 들여쓰기 레벨을 늘림
            if stripped.endswith('{') or stripped.endswith('[') or stripped.endswith('('):
                indent_level += 1

        return '\n'.join(formatted_lines)

    def _format_python_content(self, content: str) -> str:
        """Python 콘텐츠 포매팅"""
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue

            # Python의 들여쓰기는 주로 콜론으로 판단
            if any(stripped.startswith(keyword) for keyword in ['except', 'elif', 'else', 'finally']):
                current_indent = max(0, indent_level - 1)
            else:
                current_indent = indent_level

            formatted_lines.append('    ' * current_indent + stripped)

            # 콜론으로 끝나면 들여쓰기 증가
            if stripped.endswith(':'):
                indent_level += 1
            # 함수나 클래스 정의 후 빈 줄이 있으면 들여쓰기 유지
            elif stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'with ')):
                if not stripped.endswith(':'):
                    pass  # 이미 콜론 처리에서 해결

        return '\n'.join(formatted_lines)

    def _format_html_content(self, content: str) -> str:
        """HTML 콘텐츠 포매팅"""
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue

            # 닫는 태그나 특별한 케이스들 처리
            if stripped.startswith('</') and not stripped.startswith('<!--'):
                indent_level = max(0, indent_level - 1)
                formatted_lines.append('    ' * indent_level + stripped)
            # DOCTYPE 선언
            elif stripped.startswith('<!DOCTYPE'):
                formatted_lines.append(stripped)  # DOCTYPE는 들여쓰기 없음
            # 주석 처리
            elif stripped.startswith('<!--'):
                formatted_lines.append('    ' * indent_level + stripped)
            # 자체 닫는 태그들 (void elements)
            elif any(tag in stripped.lower() for tag in ['<br', '<hr', '<img', '<input', '<meta', '<link', '<area', '<base', '<col', '<embed', '<source', '<track', '<wbr']):
                formatted_lines.append('    ' * indent_level + stripped)
            # 일반 여는 태그
            elif stripped.startswith('<') and not stripped.startswith('</'):
                formatted_lines.append('    ' * indent_level + stripped)
                # 자체 닫는 태그가 아니고, 한 줄에 열고 닫는 태그가 아닌 경우만 들여쓰기 증가
                if (not stripped.endswith('/>') and
                    not self._is_single_line_tag(stripped) and
                    not any(tag in stripped.lower() for tag in ['<br', '<hr', '<img', '<input', '<meta', '<link', '<area', '<base', '<col', '<embed', '<source', '<track', '<wbr'])):
                    indent_level += 1
            # 텍스트 노드나 기타 내용
            else:
                formatted_lines.append('    ' * indent_level + stripped)

        return '\n'.join(formatted_lines)

    def _is_single_line_tag(self, line: str) -> bool:
        """한 줄에서 열고 닫는 태그인지 확인"""
        stripped = line.strip()
        # <tag>content</tag> 형태인지 확인
        if '<' in stripped and '>' in stripped:
            # 여는 태그와 닫는 태그가 같은 줄에 있는지 확인
            first_close = stripped.find('>')
            if first_close != -1 and stripped.find('</', first_close) != -1:
                return True
        return False

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

                # 파일 확장자에 따른 추가 포매팅 적용
                file_extension = full_path.suffix.lower()
                if file_extension in ['.css']:
                    processed_content = self._format_css_content(processed_content)
                elif file_extension in ['.js', '.ts', '.jsx', '.tsx']:
                    processed_content = self._format_js_ts_content(processed_content)
                elif file_extension in ['.py']:
                    processed_content = self._format_python_content(processed_content)
                elif file_extension in ['.html', '.htm']:
                    processed_content = self._format_html_content(processed_content)

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
