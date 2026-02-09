import requests
from typing import Dict, Any
from ..base import LLMProvider
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


class OllamaProvider(LLMProvider):
    """LLM Provider using local Ollama instance."""

    def __init__(self):
        self.host: str = "http://localhost:11434"
        self.model: str = "llama3"

    @property
    def name(self) -> str:
        return "ollama"

    def configure(self, config: Dict[str, Any]) -> None:
        self.host = config.get("host", self.host)
        self.model = config.get("model", self.model)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
    )
    def complete(self, prompt: str, **kwargs) -> str:
        url = f"{self.host}/api/chat"

        system_prompt = kwargs.get("system_prompt", "You are a helpful assistant.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.1),
                "num_predict": kwargs.get("max_tokens", 1024),
            },
        }

        if (
            kwargs.get("response_format")
            and kwargs["response_format"].get("type") == "json_object"
        ):
            payload["format"] = "json"

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()["message"]["content"]
