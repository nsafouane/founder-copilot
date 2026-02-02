import os
import json
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG_PATH = Path.home() / ".founder_copilot" / "config.json"

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
            "scraper_provider": "reddit",
            "storage_provider": "sqlite",
            "db_path": str(Path.home() / ".founder_copilot" / "founder_copilot.db"),
            "groq_api_key": os.getenv("GROQ_API_KEY", ""),
            "reddit_client_id": os.getenv("REDDIT_CLIENT_ID", ""),
            "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET", ""),
            "reddit_user_agent": "FounderCopilot/0.1.0",
            "subreddits": ["saas", "entrepreneur", "startups"]
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
