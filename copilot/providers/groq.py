import os
import requests
from typing import Dict, Any, Optional
from .base import LLMProvider
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class GroqProvider(LLMProvider):
    """LLM Provider using Groq API for high-speed inference."""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.model: str = "llama-3.3-70b-versatile"
        self.api_url: str = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def name(self) -> str:
        return "groq"

    def configure(self, config: Dict[str, Any]) -> None:
        self.api_key = config.get("api_key") or os.environ.get("GROQ_API_KEY")
        self.model = config.get("model", self.model)
        if not self.api_key:
            raise ValueError("Groq API key is required.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def complete(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError("GroqProvider not configured.")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = kwargs.get("system_prompt", "You are a helpful assistant.")
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "response_format": kwargs.get("response_format")
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()["choices"][0]["message"]["content"]
