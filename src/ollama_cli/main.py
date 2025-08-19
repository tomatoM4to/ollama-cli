import os

from rich.console import Console
from rich.panel import Panel

from ollama_cli.settings.ai_setup import OllamaSetup, select_from_menu
from ollama_cli.ui.app import ChatInterface
from ollama_cli.settings.config import Config

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def main():
    console = Console()

    # 시작 헤더 표시
    welcome_panel = Panel(
        "[bold bright_magenta]🦙 Ollama CLI 채팅 시스템[/bold bright_magenta]\n[dim]AI 모델과의 대화를 시작합니다...[/dim]",
        border_style="magenta",
        padding=(1, 2)
    )
    console.print(welcome_panel)

    ollama_setup = OllamaSetup(console)
    # ollama_setup.setup_ai_providers()
    ollama_installed: bool = ollama_setup.check_ollama_installation()
    if not ollama_installed:
        ollama_setup.show_ollama_installation_guide()
        return
    else:
        success_panel = Panel(
            "[green]✓ Ollama가 설치되어 있습니다.[/green]",
            border_style="green",
            padding=(0, 1)
        )
        console.print(success_panel)

    ollama_running = ollama_setup.check_ollama_service()
    if not ollama_running:
        ollama_serve = ollama_setup.run_ollama_serve()
        if not ollama_serve:
            error_panel = Panel(
                "[red]❌ Ollama 서비스 시작에 실패했습니다.[/red]",
                border_style="red",
                padding=(1, 2)
            )
            console.print(error_panel)
            return

    success_panel = Panel(
        "[green]✓ Ollama 서비스가 실행 중입니다.[/green]",
        border_style="green",
        padding=(0, 1)
    )
    console.print(success_panel)

    models: list[str] = ollama_setup.get_available_ollama_models()
    selected_model = select_from_menu(console, models, "사용 가능한 Ollama 모델", default_index=0)
    if selected_model is None:
        cancel_panel = Panel(
            "[red]❌ 모델 선택이 취소되었습니다.[/red]",
            border_style="red",
            padding=(1, 2)
        )
        console.print(cancel_panel)
        return

    load_model: bool = ollama_setup.load_model(selected_model)

    if not load_model:
        error_panel = Panel(
            "[red]❌ 모델 로드에 실패했습니다.[/red]",
            border_style="red",
            padding=(1, 2)
        )
        console.print(error_panel)
        return

    # 채팅 시작 안내
    ready_panel = Panel(
        f"[bold bright_magenta]✨ 모든 설정이 완료되었습니다![/bold bright_magenta]\n[bright_white]모델: {selected_model}[/bright_white]\n[dim]채팅을 시작합니다...[/dim]",
        border_style="green",
        padding=(1, 2)
    )
    console.print(ready_panel)

    config = Config(
        platform='Ollama',
        model=selected_model
    )

    app = ChatInterface(config)
    app.run()

if __name__ == "__main__":
    main()
