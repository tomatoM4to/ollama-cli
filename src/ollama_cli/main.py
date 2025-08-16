import os

from ollama_cli.settings.settings import Settings, load_user_settings
from ollama_cli.ui.app import ChatInterface
from provider.anthropic import AnthropicProvider
from provider.ollama import OllamaProvider
from provider.openai import OpenAIProvider
from provider.provider import MultiLLMClient

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def main():
    user_settings: Settings | None = load_user_settings()

    if user_settings is None:
        return

    client = MultiLLMClient()

    if OPENAI_API_KEY:
        client.add_provider("openai", OpenAIProvider(OPENAI_API_KEY))

    if ANTHROPIC_API_KEY:
        client.add_provider("anthropic", AnthropicProvider(ANTHROPIC_API_KEY))

    client.add_provider("ollama", OllamaProvider())

    if user_settings.default == "openai":
        print("Using OpenAI as the default provider.")
    elif user_settings.default == "anthropic":
        print("Using Anthropic as the default provider.")
    elif user_settings.default == "ollama":
        print("Using Ollama as the default provider.")

    app = ChatInterface()
    app.run()

if __name__ == "__main__":
    main()
