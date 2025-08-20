import fnmatch
from pathlib import Path
from typing import TypedDict


class PlanningResult(TypedDict):
    analysis: str
    files_to_read: list[str]
    files_to_create: list[str]
    files_to_modify: list[str]
    dependencies_required: list[str]


class PlanningAgent:
    def get_directory_structure(self, path='.', custom_ignores=None):
        # 기본 ignore 패턴들
        ignore_patterns = [
            '.venv', 'venv', '.env',
            '__pycache__', '*.pyc', '.pytest_cache',
            '.git', '.gitignore',
            'node_modules', '.npm',
            '.DS_Store', 'Thumbs.db',
            '*.log',
            '.uvlock', 'uv.lock',
            '.idea', '.vscode',
            'dist', 'build', '*.egg-info',
            '.mypy_cache', '.coverage'
        ]

        if custom_ignores:
            ignore_patterns.extend(custom_ignores)

        def should_ignore(name):
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(name, pattern):
                    return True
            return False

        def build_tree(directory, prefix=''):
            directory = Path(directory)
            lines = []

            if directory.is_dir():
                # 필터링된 항목들만 가져오기
                contents = [item for item in directory.iterdir()
                           if not should_ignore(item.name)]

                for i, item in enumerate(contents):
                    is_last = i == len(contents) - 1
                    current_prefix = '└── ' if is_last else '├── '

                    if item.is_dir():
                        lines.append(f'{prefix}{current_prefix}{item.name}/')
                        next_prefix = prefix + ('    ' if is_last else '│   ')
                        lines.extend(build_tree(item, next_prefix))
                    else:
                        lines.append(f'{prefix}{current_prefix}{item.name}')

            return lines

        tree_lines = build_tree(path)
        return '\n'.join(tree_lines)

    def check_planning_result(self, data: dict) -> bool:
        """
        PlanningResult 형식이 맞는지 확인하는 메서드

        Args:
            data: 검증할 딕셔너리 데이터

        Returns:
            bool: PlanningResult 형식이 맞으면 True, 아니면 False
        """
        required_keys = ['analysis', 'files_to_read', 'files_to_create', 'files_to_modify', 'dependencies_required']

        # 모든 필수 키가 있는지 확인
        if not all(key in data for key in required_keys):
            return False

        # 타입 검증
        if not isinstance(data['analysis'], str):
            return False

        # 리스트 타입 검증
        list_keys = ['files_to_read', 'files_to_create', 'files_to_modify', 'dependencies_required']
        for key in list_keys:
            if not isinstance(data[key], list):
                return False
            # 리스트 내 모든 요소가 문자열인지 확인
            if not all(isinstance(item, str) for item in data[key]):
                return False

        return True

    def format_planning_result_to_markdown(self, data: dict) -> str:
        """
        PlanningResult를 마크다운 형식으로 변환하는 메서드

        Args:
            data: PlanningResult 딕셔너리

        Returns:
            str: 마크다운 형식의 문자열
        """
        markdown = "# 📋 Planning Result\n\n"

        # Analysis 섹션
        markdown += "## 🔍 Analysis\n"
        markdown += f"{data['analysis']}\n\n"

        # Files to Read 섹션
        markdown += "## 📖 Files to Read\n"
        if data['files_to_read']:
            for file in data['files_to_read']:
                markdown += f"- `{file}`\n"
        else:
            markdown += "- No files to read\n"
        markdown += "\n"

        # Files to Create 섹션
        markdown += "## ✨ Files to Create\n"
        if data['files_to_create']:
            for file in data['files_to_create']:
                markdown += f"- `{file}`\n"
        else:
            markdown += "- No files to create\n"
        markdown += "\n"

        # Files to Modify 섹션
        markdown += "## ✏️ Files to Modify\n"
        if data['files_to_modify']:
            for file in data['files_to_modify']:
                markdown += f"- `{file}`\n"
        else:
            markdown += "- No files to modify\n"
        markdown += "\n"

        # Dependencies Required 섹션
        markdown += "## 📦 Dependencies Required\n"
        if data['dependencies_required']:
            for dep in data['dependencies_required']:
                markdown += f"- `{dep}`\n"
        else:
            markdown += "- No additional dependencies required\n"

        return markdown
