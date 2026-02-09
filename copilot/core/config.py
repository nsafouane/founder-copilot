import os
import json
from pathlib import Path
from typing import Dict, Any, List

DEFAULT_CONFIG_PATH = Path.home() / ".founder_copilot" / "config.json"

SAAS_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "high": [
        "paying for",
        "subscription",
        "monthly fee",
        "enterprise",
        "API",
        "B2B",
        "SaaS",
        "willing to pay",
        "shut up and take my money",
    ],
    "medium": [
        "alternative to",
        "looking for",
        "better tool",
        "recommend",
        "comparison",
        "vs",
        "switch from",
        "migrate",
    ],
    "low": [
        "how do I",
        "tutorial",
        "help with",
        "frustrated with",
        "wish there was",
        "why doesn't",
    ],
}


class ConfigManager:
    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self._config: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return self._default_config()

        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception:
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        return {
            "llm_provider": "groq",
            "llm_request_delay": 2,
            "active_scrapers": ["reddit"],
            "default_scraper": "reddit",
            "storage_provider": "sqlite",
            "db_path": str(Path.home() / ".founder_copilot" / "founder_copilot.db"),
            "groq_api_key": os.getenv("GROQ_API_KEY", ""),
            "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
            "reddit_client_id": os.getenv("REDDIT_CLIENT_ID", ""),
            "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET", ""),
            "reddit_user_agent": "FounderCopilot/1.1.0",
            "subreddits": ["saas", "entrepreneur", "startups"],
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3",
            "apify_api_token": os.getenv("APIFY_API_TOKEN", ""),
        }

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._config, f, indent=4)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        self._config[key] = value
        self.save()

    @property
    def all(self) -> Dict[str, Any]:
        return self._config
