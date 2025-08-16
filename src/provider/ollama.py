import json
from collections.abc import Iterator

import requests

from provider.provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "exaone-deep:7.8b"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.session = requests.Session()

    def chat_stream(self, message: str) -> Iterator[str]:
        url = f"{self.base_url}/api/generate"

        prompt = message

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                stream=True,
                timeout=30
            )
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            content = chunk["response"]
                            if content:
                                yield content

                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to Ollama server: {e}")from e
