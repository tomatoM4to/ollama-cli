import os

from ollama_cli.settings.settings import Settings, load_user_settings
from ollama_cli.ui.app import ChatInterface
from provider.anthropic import AnthropicProvider
from provider.ollama import OllamaProvider
from provider.openai import OpenAIProvider
from provider.provider import MultiLLMClient
from ollama_cli.settings.ai_setup import OllamaSetup, select_from_menu
from rich.console import Console

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def main():
    console = Console()
    ollama_setup = OllamaSetup(console)
    # ollama_setup.setup_ai_providers()
    ollama_installed: bool = ollama_setup.check_ollama_installation()
    if not ollama_installed:
        ollama_setup.show_ollama_installation_guide()
        return
    else:
        console.print("[green]✓ Ollama가 설치되어 있습니다.[/green]")

    ollama_running = ollama_setup.check_ollama_service()
    if not ollama_running:
        ollama_serve = ollama_setup.run_ollama_serve()
        if not ollama_serve:
            console.print("[red]❌ Ollama 서비스 시작에 실패했습니다.[/red]")
            return
    console.print("[green]✓ Ollama 서비스가 실행 중입니다.[/green]")

    models: list[str] = ollama_setup.get_available_ollama_models()
    selected_model = select_from_menu(console, models, "사용 가능한 Ollama 모델", default_index=0)
    if selected_model is None:
        console.print("[red]❌ 모델 선택이 취소되었습니다.[/red]")
        return

    load_model: bool = ollama_setup.load_model(selected_model)

    if not load_model:
        console.print("[red]❌ 모델 로드에 실패했습니다.[/red]")
        return

    user_settings: Settings | None = load_user_settings()

    if user_settings is None:
        return

    client = MultiLLMClient()

    if OPENAI_API_KEY:
        client.add_provider("openai", OpenAIProvider(OPENAI_API_KEY))

    if ANTHROPIC_API_KEY:
        client.add_provider("anthropic", AnthropicProvider(ANTHROPIC_API_KEY))

    client.add_provider("ollama", OllamaProvider(model=selected_model))

    app = ChatInterface(selected_model)
    app.run()

if __name__ == "__main__":
    main()
