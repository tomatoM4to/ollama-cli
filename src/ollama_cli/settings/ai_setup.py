from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
import time
import subprocess

def select_from_menu(
    console: Console,
    options: list[str],
    title: str,
    default_index: int = 0
) -> str | None:
    """
    Ags:
        options: 선택 가능한 옵션들
        title: 메뉴 제목
        show_numbers: 번호 표시 여부
        default_index: 기본 선택 인덱스
    Returns:
        선택된 옵션 인덱스, 취소시 None
    """

    if not options:
        return None

    console.print(f"\n[bold cyan]{title}[/bold cyan]")

    table = Table(box=None, padding=(0, 2))
    table.add_column("번호", style="cyan", width=4)
    table.add_column("옵션", style="white")

    for i, option in enumerate(options, 1):
        style = "bold green"
        table.add_row(f"[cyan]{i}[/cyan]", f"[{style}]{option}[/{style}]")

    console.print(table)

    # 선택지 생성
    choices = [str(i) for i in range(1, len(options) + 1)]
    choices.append("q")

    choice = Prompt.ask(
        "번호를 선m택하세요 (q: 취소)",
        choices=choices,
        default=str(default_index + 1)
    )

    if choice == "q":
        return None

    return options[int(choice) - 1]


class OllamaSetup:
    def __init__(self, console: Console):
        self.console = console
        self.settings_path = Path.cwd() / ".ocli" / "settings.json"
        self.api_url = "http://localhost:11434/api"

    def check_ollama_installation(self) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def check_ollama_service(self) -> bool:
        self.console.print("[bold green]🔍 Ollama 서비스 상태를 확인합니다...[/bold green]")
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=3)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_available_ollama_models(self) -> list[str]:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            models = []
            lines = result.stdout.strip().split('\n')[1:]  # 헤더 제외
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)

            return models
        except (subprocess.SubprocessError, FileNotFoundError):
            return []

    def show_install_recommend_ollama_model(self):
        recommended_models = [
            ('gpt-oss:20b', 'OpenAI’s open-weight models designed for powerful reasoning, agentic tasks, and versatile developer use cases. (14GB)', ),
            ('deepseek-r1:8b', 'DeepSeek-R1 is a family of open reasoning models with performance approaching that of leading models, such as O3 and Gemini 2.5 Pro. (5.2GB)'),
            ('gemma3:4b', 'The current, most capable model that runs on a single GPU. (3.3GB)')
        ]

        self.console.print("\n[cyan]📦 권장 Ollama 모델:[/cyan]")

        table = Table()
        table.add_column('번호', style='cyan')
        table.add_column('모델명', style='green')
        table.add_column('설명', style='white')

        for i, (model, description) in enumerate(recommended_models, 1):
            table.add_row(str(i), model, description)

        self.console.print(table)

        choice = Prompt.ask(
            "설치할 모델 번호를 선택하세요 (1-3, 또는 's'로 건너뛰기)",
            choices=["1", "2", "3", "s"],
            default="1"
        )

        if choice == 's':
            self.console.print("[yellow]모델 설치를 건너뜁니다.[/yellow]")
            return False

        model_to_install = recommended_models[int(choice) - 1][0]

        self.console.print(f"\n[yellow]📥 {model_to_install} 모델을 다운로드 중...[/yellow]")
        self.console.print("[dim]이 작업은 몇 분이 걸릴 수 있습니다.[/dim]")

        try:
            # ollama pull 명령어 실행
            process = subprocess.Popen(
                ["ollama", "pull", model_to_install],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 실시간 출력
            if process.stdout is not None:
                for line in process.stdout:
                    self.console.print(f"  {line.strip()}")

            process.wait()

            if process.returncode == 0:
                self.console.print(f"\n[green]✓ {model_to_install} 모델이 성공적으로 설치되었습니다![/green]")
                return True
            else:
                self.console.print(f"\n[red]❌ 모델 설치 중 오류가 발생했습니다.[/red]")
                return False

        except subprocess.SubprocessError as e:
            self.console.print(f"\n[red]❌ 모델 설치 실패: {e}[/red]")
            return False

    def show_ollama_installation_guide(self):
        self.console.print("[red]❌ Ollama가 설치되어 있지 않습니다.[/red]")

        """Ollama 설치 가이드 표시"""
        guide = """
[bold cyan]Ollama 설치 방법:[/bold cyan]

[yellow]macOS:[/yellow]
curl -fsSL https://ollama.com/install.sh | sh

[yellow]Linux:[/yellow]
curl -fsSL https://ollama.com/install.sh | sh

[yellow]Windows:[/yellow]
https://ollama.com/download/windows 에서 다운로드

설치 후 터미널에서 'ollama serve'를 실행하여 서비스를 시작하세요.
        """

        panel = Panel(
            guide,
            title="🦙 Ollama 설치 가이드",
            border_style="green"
        )
        self.console.print(panel)

    def run_model(self, model: str):
        self.console.print(f"[bold green]🤖 {model} 모델을 실행합니다...[/bold green]")
        try:
            subprocess.run(["ollama", "run", model], check=True)
            self.console.print(f"[green]✓ {model} 모델이 성공적으로 실행되었습니다.[/green]")
        except subprocess.CalledProcessError:
            self.console.print(f"[red]❌ {model} 모델 실행에 실패했습니다.[/red]")

    def run_ollama_serve(self) -> bool:
        self.console.print("[yellow]🚀 Ollama 서비스를 시작합니다...[/yellow]")

        subprocess.Popen(
            ['ollama', 'serve'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        for i in range(10):
            time.sleep(1)
            if self.check_ollama_service():
                return True

        return False

    def load_model(self, model_name: str) -> bool:
        self.console.print(f"[yellow]🔄 {model_name} 모델을 로드합니다...[/yellow]")

        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json={
                    "model": model_name,
                    "prompt": "Hello",
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                self.console.print(f"[green]✓ {model_name} 모델이 성공적으로 로드되었습니다.[/green]")
                return True
            else:
                self.console.print(f"[red]❌ {model_name} 모델 로드 실패: {response.status_code}[/red]")
                return False

        except Exception as e:
            self.console.print(f"[red]❌ 모델 로드 실패: {e}[/red]")
            return False

    def setup_ai_providers(self):
        """AI Provider 설정 프로세스 실행"""
        self.console.print("[bold green]🤖 Ollama 가 설치되어있는지 확인합니다...[/bold green]")

        # 1. Ollama 확인
        ollama_installed: bool = self.check_ollama_installation()
        if not ollama_installed:
            self.console.print("[red]❌ Ollama가 설치되어 있지 않습니다.[/red]")
            self.show_ollama_installation_guide()
            return False

        self.console.print("[green]✓ Ollama가 설치되어 있습니다.[/green]")
        self.console.print("[bold green]🔍 Ollama 서비스 상태를 확인합니다...[/bold green]")
        ollama_running = self.check_ollama_service()

        if not ollama_running:
            self.console.print("[yellow]⚠️ Ollama 서비스가 실행되지 않았습니다.[/yellow]")
            return False

        self.console.print("[green]✓ Ollama 서비스가 실행 중입니다.[/green]")

        self.console.print("[bold green]📦 사용 가능한 모델을 확인합니다...[/bold green]")

        models: list[str] = self.get_available_ollama_models()
        selected_model = select_from_menu(self.console, models, "사용 가능한 Ollama 모델", default_index=0)
        if selected_model is None:
            return False

        serve = self.run_ollama_serve()
        if not serve:
            self.console.print("[red]❌ Ollama 서비스를 시작하는데 실패했습니다.[/red]")
            return

        load_model = self.load_model(selected_model)
        if not load_model:
            self.console.print("[red]❌ 모델을 로드하는데 실패했습니다.[/red]")
            return False

        return True