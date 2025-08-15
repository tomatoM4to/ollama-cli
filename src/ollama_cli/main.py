import os

from ollama_cli.settings.settings import Settings, load_user_settings

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def main():
    user_settings: Settings | None = load_user_settings()

    if user_settings is None:
        return

    if user_settings.default == "openai":
        print("Using OpenAI as the default provider.")
    elif user_settings.default == "anthropic":
        print("Using Anthropic as the default provider.")
    elif user_settings.default == "ollama":
        print("Using Ollama as the default provider.")

if __name__ == "__main__":
    main()
