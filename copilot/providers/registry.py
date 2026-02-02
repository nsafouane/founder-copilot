from typing import Dict, Any, Type, Optional
from .base import ScraperProvider, LLMProvider, StorageProvider

class ProviderRegistry:
    """Registry for managing swappable providers."""
    
    def __init__(self):
        self._scrapers: Dict[str, ScraperProvider] = {}
        self._llms: Dict[str, LLMProvider] = {}
        self._storage: Dict[str, StorageProvider] = {}

    def register_scraper(self, provider: ScraperProvider):
        self._scrapers[provider.name] = provider

    def register_llm(self, provider: LLMProvider):
        self._llms[provider.name] = provider

    def register_storage(self, provider: StorageProvider):
        self._storage[provider.name] = provider

    def get_scraper(self, name: str) -> ScraperProvider:
        if name not in self._scrapers:
            raise ValueError(f"Scraper provider '{name}' not found")
        return self._scrapers[name]

    def get_llm(self, name: str) -> LLMProvider:
        if name not in self._llms:
            raise ValueError(f"LLM provider '{name}' not found")
        return self._llms[name]

    def get_storage(self, name: str) -> StorageProvider:
        if name not in self._storage:
            raise ValueError(f"Storage provider '{name}' not found")
        return self._storage[name]
