import pytest
from copilot.providers.registry import ProviderRegistry
from copilot.providers.base import ScraperProvider, LLMProvider, StorageProvider
from unittest.mock import MagicMock

class MockScraper(ScraperProvider):
    @property
    def name(self): return "mock_scraper"
    def configure(self, config): pass
    def scrape(self, source, target, limit=100, **kwargs): return []

class MockLLM(LLMProvider):
    @property
    def name(self): return "mock_llm"
    def configure(self, config): pass
    def complete(self, prompt, **kwargs): return "response"

class MockStorage(StorageProvider):
    @property
    def name(self): return "mock_storage"
    def configure(self, config): pass
    def store_posts(self, posts): return 0

def test_registry_registration():
    registry = ProviderRegistry()
    scraper = MockScraper()
    llm = MockLLM()
    storage = MockStorage()
    
    registry.register_scraper(scraper)
    registry.register_llm(llm)
    registry.register_storage(storage)
    
    assert registry.get_scraper("mock_scraper") == scraper
    assert registry.get_llm("mock_llm") == llm
    assert registry.get_storage("mock_storage") == storage

def test_registry_not_found():
    registry = ProviderRegistry()
    with pytest.raises(ValueError):
        registry.get_scraper("none")
