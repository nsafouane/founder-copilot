from typing import Dict, Any, Type, Optional, List, Set
from .base import ScraperProvider, LLMProvider, ScraperCapability, CRMProvider
from .storage.base import StorageProvider
from .llm.ollama import OllamaProvider
from .storage.sqlite_provider import SQLiteProvider
from .scrapers.indiehackers import IndieHackersScraper
from .crm.hubspot_provider import HubSpotProvider
from .crm.salesforce_provider import SalesForceProvider


class ProviderRegistry:
    """Service locator with capability querying and multi-scraper support."""

    def __init__(self):
        self._scrapers: Dict[str, ScraperProvider] = {}
        self._llms: Dict[str, LLMProvider] = {}
        self._storage: Dict[str, StorageProvider] = {}
        self._crm: Dict[str, CRMProvider] = {}

        # Register built-in providers
        self.register_scraper(IndieHackersScraper())
        # Example of registering a built-in LLM and Storage
        self.register_llm(OllamaProvider()) # Assuming a default/mock config for now
        self.register_storage(SQLiteProvider()) # Assuming a default path for now
        self.register_crm(HubSpotProvider()) # Register HubSpot CRM
        self.register_crm(SalesForceProvider()) # Register SalesForce CRM


    # --- Registration ---
    def register_scraper(self, provider: ScraperProvider) -> None:
        self._scrapers[provider.name] = provider

    def register_llm(self, provider: LLMProvider) -> None:
        self._llms[provider.name] = provider

    def register_storage(self, provider: StorageProvider) -> None:
        self._storage[provider.name] = provider

    def register_crm(self, provider: CRMProvider) -> None:
        self._crm[provider.name] = provider

    # --- Retrieval ---
    def get_scraper(self, name: str) -> ScraperProvider:
        if name not in self._scrapers:
            available = ", ".join(self._scrapers.keys()) or "(none)"
            raise ValueError(f"Scraper '{name}' not registered. Available: {available}")
        return self._scrapers[name]

    def get_llm(self, name: str) -> LLMProvider:
        if name not in self._llms:
            available = ", ".join(self._llms.keys()) or "(none)"
            raise ValueError(f"LLM '{name}' not registered. Available: {available}")
        return self._llms[name]

    def get_storage(self, name: str) -> StorageProvider:
        if name not in self._storage:
            raise ValueError(f"Storage '{name}' not registered.")
        return self._storage[name]
    
    def get_crm(self, name: str) -> CRMProvider:
        if name not in self._crm:
            available = ", ".join(self._crm.keys()) or "(none)"
            raise ValueError(f"CRM '{name}' not registered. Available: {available}")
        return self._crm[name]

    def get_all_scrapers(self) -> List[ScraperProvider]:
        """Return all registered scrapers."""
        return list(self._scrapers.values())

    def get_scrapers_with_capability(
        self, cap: ScraperCapability
    ) -> List[ScraperProvider]:
        """Return scrapers that declare a specific capability."""
        return [s for s in self._scrapers.values() if cap in s.capabilities]

    def list_scraper_names(self) -> List[str]:
        """Return names of all registered scrapers."""
        return list(self._scrapers.keys())

    def list_llm_names(self) -> List[str]:
        return list(self._llms.keys())
