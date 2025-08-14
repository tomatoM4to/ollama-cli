import os

from provider.anthropic import AnthropicProvider
from provider.openai import OpenAIProvider
from provider.provider import MultiLLMClient

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


def main():
    client: MultiLLMClient = MultiLLMClient()

    client.add_provider("openai", OpenAIProvider(OPENAI_API_KEY))
    client.add_provider("anthropic", AnthropicProvider(ANTHROPIC_API_KEY))

    for chunk in client.chat_stream("openai", "자기소개 부탁해"):
        print(chunk, end="", flush=True)

    print()
    print("=" * 10)

    for chunk in client.chat_stream("anthropic", "자기소개 부탁해"):
        print(chunk, end="", flush=True)


if __name__ == "__main__":
    main()
