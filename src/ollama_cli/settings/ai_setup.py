from pathlib import Path
import threading

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
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

    # 밝은 보라색을 위주로 한 스타일링
    header_panel = Panel(
        f"[bold bright_magenta]{title}[/bold bright_magenta]",
        border_style="magenta",
        padding=(1, 2)
    )
    console.print(header_panel)

    table = Table(
        box=None,
        padding=(0, 2),
        border_style="bright_magenta",
        header_style="bold bright_magenta"
    )
    table.add_column("번호", style="bright_cyan", width=6, justify="center")
    table.add_column("옵션", style="bright_white")

    for i, option in enumerate(options, 1):
        # 기본 선택 항목을 더 눈에 띄게 표시
        if i == default_index + 1:
            style = "bold bright_magenta on grey23"
            indicator = "→ "
        else:
            style = "bright_white"
            indicator = "  "

        table.add_row(
            f"[bright_cyan]{i}[/bright_cyan]",
            f"[{style}]{indicator}{option}[/{style}]"
        )

    console.print(table)

    # 선택지 생성
    choices = [str(i) for i in range(1, len(options) + 1)]
    choices.append("q")

    choice_panel = Panel(
        "[bright_magenta]번호를 선택하세요[/bright_magenta] [dim](q: 취소)[/dim]",
        border_style="bright_magenta",
        padding=(0, 1)
    )
    console.print(choice_panel)

    choice = Prompt.ask(
        "[bright_magenta]선택",
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
        status_panel = Panel(
            "[bold bright_magenta]🔍 Ollama 서비스 상태를 확인합니다...[/bold bright_magenta]",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(status_panel)

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

        self.console.print("\n[bright_magenta]📦 권장 Ollama 모델:[/bright_magenta]")

        table = Table(border_style="bright_magenta", header_style="bold bright_magenta")
        table.add_column('번호', style='bright_cyan', justify='center', width=6)
        table.add_column('모델명', style='bright_magenta')
        table.add_column('설명', style='bright_white')

        for i, (model, description) in enumerate(recommended_models, 1):
            table.add_row(str(i), model, description)

        self.console.print(table)

        choice = Prompt.ask(
            "[bright_magenta]설치할 모델 번호를 선택하세요 (1-3, 또는 's'로 건너뛰기)[/bright_magenta]",
            choices=["1", "2", "3", "s"],
            default="1"
        )

        if choice == 's':
            self.console.print(Panel(
                "[yellow]모델 설치를 건너뜁니다.[/yellow]",
                border_style="yellow",
                padding=(0, 1)
            ))
            return False

        model_to_install = recommended_models[int(choice) - 1][0]

        download_panel = Panel(
            f"[bright_magenta]📥 {model_to_install} 모델을 다운로드 중...[/bright_magenta]\n[dim]이 작업은 몇 분이 걸릴 수 있습니다.[/dim]",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(download_panel)

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
                    self.console.print(f"  [bright_cyan]▶[/bright_cyan] {line.strip()}")

            process.wait()

            if process.returncode == 0:
                success_panel = Panel(
                    f"[bold green]✓ {model_to_install} 모델이 성공적으로 설치되었습니다![/bold green]",
                    border_style="green",
                    padding=(1, 2)
                )
                self.console.print(success_panel)
                return True
            else:
                error_panel = Panel(
                    "[red]❌ 모델 설치 중 오류가 발생했습니다.[/red]",
                    border_style="red",
                    padding=(1, 2)
                )
                self.console.print(error_panel)
                return False

        except subprocess.SubprocessError as e:
            error_panel = Panel(
                f"[red]❌ 모델 설치 실패: {e}[/red]",
                border_style="red",
                padding=(1, 2)
            )
            self.console.print(error_panel)
            return False

    def show_ollama_installation_guide(self):
        error_panel = Panel(
            "[red]❌ Ollama가 설치되어 있지 않습니다.[/red]",
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(error_panel)

        """Ollama 설치 가이드 표시"""
        guide = """
[bold bright_magenta]Ollama 설치 방법:[/bold bright_magenta]

[bright_cyan]macOS:[/bright_cyan]
curl -fsSL https://ollama.com/install.sh | sh

[bright_cyan]Linux:[/bright_cyan]
curl -fsSL https://ollama.com/install.sh | sh

[bright_cyan]Windows:[/bright_cyan]
https://ollama.com/download/windows 에서 다운로드

설치 후 터미널에서 'ollama serve'를 실행하여 서비스를 시작하세요.
        """

        panel = Panel(
            guide,
            title="🦙 Ollama 설치 가이드",
            border_style="magenta"
        )
        self.console.print(panel)

    def run_model(self, model: str):
        run_panel = Panel(
            f"[bold bright_magenta]🤖 {model} 모델을 실행합니다...[/bold bright_magenta]",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(run_panel)

        try:
            subprocess.run(["ollama", "run", model], check=True)
            success_panel = Panel(
                f"[green]✓ {model} 모델이 성공적으로 실행되었습니다.[/green]",
                border_style="green",
                padding=(1, 2)
            )
            self.console.print(success_panel)
        except subprocess.CalledProcessError:
            error_panel = Panel(
                f"[red]❌ {model} 모델 실행에 실패했습니다.[/red]",
                border_style="red",
                padding=(1, 2)
            )
            self.console.print(error_panel)

    def run_ollama_serve(self) -> bool:
        start_panel = Panel(
            "[bright_magenta]🚀 Ollama 서비스를 시작합니다...[/bright_magenta]",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(start_panel)

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
        """모델 로드 시 실시간 타이머와 함께 진행 상황 표시"""
        start_time = time.time()
        is_loading = True

        def loading_timer():
            """백그라운드에서 실행될 타이머 함수"""
            while is_loading:
                elapsed = time.time() - start_time
                return f"[bright_cyan]{elapsed:.1f}초[/bright_cyan]"

        # Layout 구성
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", size=5)
        )

        # 헤더 구성
        header_text = Panel(
            f"[bold bright_magenta]🔄 {model_name} 모델을 로드합니다...[/bold bright_magenta]",
            border_style="magenta",
            padding=(0, 2)
        )

        # 메인 영역 구성 (스피너 + 타이머)
        def create_main_content():
            elapsed = time.time() - start_time
            spinner_text = Text()
            spinner_text.append("로딩 중", style="bright_magenta")
            spinner_text.append(" • ", style="dim")
            spinner_text.append(f"{elapsed:.1f}초", style="bright_cyan")

            return Panel(
                Align.center(
                    Columns([
                        Spinner("dots", text=spinner_text, style="bright_magenta"),
                        Text(f"[bright_cyan]소요 시간: {elapsed:.1f}초[/bright_cyan]")
                    ], align="center")
                ),
                border_style="magenta",
                padding=(1, 2)
            )

        # Live 디스플레이로 실시간 업데이트
        with Live(layout, refresh_per_second=10, console=self.console, auto_refresh=True) as live:
            layout["header"].update(header_text)

            def update_display():
                while is_loading:
                    layout["main"].update(create_main_content())
                    time.sleep(0.1)

            # 업데이트 스레드 시작
            update_thread = threading.Thread(target=update_display, daemon=True)
            update_thread.start()

            try:
                response = requests.post(
                    f"{self.api_url}/generate",
                    json={
                        "model": model_name,
                        "prompt": "Hello",
                        "stream": False
                    },
                    timeout=60
                )

                is_loading = False
                elapsed_time = time.time() - start_time

                if response.status_code == 200:
                    success_panel = Panel(
                        f"[bold green]✓ {model_name} 모델이 성공적으로 로드되었습니다![/bold green]\n[dim]소요 시간: {elapsed_time:.1f}초[/dim]",
                        border_style="green",
                        padding=(1, 2)
                    )
                    live.update(success_panel)
                    time.sleep(2)  # 결과를 잠시 보여줌
                    return True
                else:
                    error_panel = Panel(
                        f"[red]❌ {model_name} 모델 로드 실패: {response.status_code}[/red]\n[dim]소요 시간: {elapsed_time:.1f}초[/dim]",
                        border_style="red",
                        padding=(1, 2)
                    )
                    live.update(error_panel)
                    time.sleep(2)
                    return False

            except Exception as e:
                is_loading = False
                elapsed_time = time.time() - start_time
                error_panel = Panel(
                    f"[red]❌ 모델 로드 실패: {e}[/red]\n[dim]소요 시간: {elapsed_time:.1f}초[/dim]",
                    border_style="red",
                    padding=(1, 2)
                )
                live.update(error_panel)
                time.sleep(2)
                return False

    def setup_ai_providers(self):
        """AI Provider 설정 프로세스 실행"""
        setup_panel = Panel(
            "[bold bright_magenta]🤖 Ollama 설정을 시작합니다...[/bold bright_magenta]",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(setup_panel)

        # 1. Ollama 확인
        ollama_installed: bool = self.check_ollama_installation()
        if not ollama_installed:
            error_panel = Panel(
                "[red]❌ Ollama가 설치되어 있지 않습니다.[/red]",
                border_style="red",
                padding=(1, 2)
            )
            self.console.print(error_panel)
            self.show_ollama_installation_guide()
            return False

        success_panel = Panel(
            "[green]✓ Ollama가 설치되어 있습니다.[/green]",
            border_style="green",
            padding=(0, 1)
        )
        self.console.print(success_panel)

        ollama_running = self.check_ollama_service()

        if not ollama_running:
            warning_panel = Panel(
                "[yellow]⚠️ Ollama 서비스가 실행되지 않았습니다.[/yellow]",
                border_style="yellow",
                padding=(1, 2)
            )
            self.console.print(warning_panel)
            return False

        success_panel = Panel(
            "[green]✓ Ollama 서비스가 실행 중입니다.[/green]",
            border_style="green",
            padding=(0, 1)
        )
        self.console.print(success_panel)

        models_panel = Panel(
            "[bold bright_magenta]📦 사용 가능한 모델을 확인합니다...[/bold bright_magenta]",
            border_style="magenta",
            padding=(1, 2)
        )
        self.console.print(models_panel)

        models: list[str] = self.get_available_ollama_models()
        selected_model = select_from_menu(self.console, models, "사용 가능한 Ollama 모델", default_index=0)
        if selected_model is None:
            return False

        serve = self.run_ollama_serve()
        if not serve:
            error_panel = Panel(
                "[red]❌ Ollama 서비스를 시작하는데 실패했습니다.[/red]",
                border_style="red",
                padding=(1, 2)
            )
            self.console.print(error_panel)
            return

        load_model = self.load_model(selected_model)
        if not load_model:
            error_panel = Panel(
                "[red]❌ 모델을 로드하는데 실패했습니다.[/red]",
                border_style="red",
                padding=(1, 2)
            )
            self.console.print(error_panel)
            return False

        return True