import pytest
from copilot.providers.registry import ProviderRegistry
from copilot.providers.base import ScraperProvider, LLMProvider
from copilot.providers.storage.base import StorageProvider
from copilot.models.schemas import ScrapedPost, PainScore
from unittest.mock import MagicMock


class MockScraper(ScraperProvider):
    @property
    def name(self):
        return "mock_scraper"

    @property
    def platform(self):
        return "Mock"

    @property
    def capabilities(self):
        return set()

    def configure(self, config):
        pass

    def scrape(self, target, limit=100, **kwargs):
        return []


class MockLLM(LLMProvider):
    @property
    def name(self):
        return "mock_llm"

    def configure(self, config):
        pass

    def complete(self, prompt, **kwargs):
        return "response"


class MockStorage(StorageProvider):
    @property
    def name(self):
        return "mock_storage"

    def initialize(self):
        pass

    def save_post(self, post):
        pass

    def get_posts(self, limit=100, source=None):
        return []

    def get_post_by_id(self, post_id):
        return None

    def save_signal(self, post_id, pain_info):
        pass

    def get_signal(self, post_id):
        return None

    def save_opportunity_score(self, score):
        pass

    def get_opportunity_scores(self, limit=100, min_score=0.0):
        return []

    def save_lead(self, lead):
        pass

    def get_leads(self, limit=None):
        return []

    def save_report(self, report):
        pass

    def get_reports(self, limit=None):
        return []


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
