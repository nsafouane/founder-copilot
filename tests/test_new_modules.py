import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from copilot.models.schemas import ScrapedPost, PainScore
from copilot.modules.discovery import DiscoveryModule
from copilot.modules.validation import ValidationModule
from copilot.modules.monitor import MonitorModule
from copilot.modules.leads import LeadModule

class MockScraper:
    def scrape(self, source, target, limit):
        return [
            ScrapedPost(
                id=f"test_{i}",
                source="reddit",
                title=f"Problem {i} with something",
                body="I really hate how this works",
                author="user1",
                url="http://test.com",
                upvotes=10,
                comments_count=5,
                created_at=datetime.now(timezone.utc),
                subreddit="test_sub"
            ) for i in range(limit)
        ]

class MockLLM:
    def complete(self, prompt, system_prompt=None, response_format=None):
        if "validation" in prompt.lower() or "research" in prompt.lower():
            return '{"idea_summary": "Test Idea", "market_size_estimate": "Big", "competitors": [], "swot_analysis": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}, "validation_verdict": "Go", "next_steps": []}'
        if "intent" in prompt.lower():
            return '{"intent_score": 0.8, "content_snippet": "Needs help", "reasoning": "Clear intent"}'
        return '{"score": 0.9, "reasoning": "High pain", "detected_problems": ["prob1"], "suggested_solutions": ["sol1"], "validation_score": 0.8}'

class MockStorage:
    def __init__(self):
        self.posts = []
        self.signals = {}
        self.leads = []
    def initialize(self): pass
    def save_post(self, post): self.posts.append(post)
    def save_signal(self, post_id, pain_info): self.signals[post_id] = pain_info
    def get_posts(self, limit=100): return self.posts
    def save_lead(self, lead): self.leads.append(lead)
    def get_leads(self, limit=100): return self.leads

def test_validation_module():
    llm = MockLLM()
    storage = MockStorage()
    post = ScrapedPost(
        id="p1", source="reddit", title="Pain", author="a", url="u", 
        upvotes=1, comments_count=1, created_at=datetime.now()
    )
    storage.save_post(post)
    
    module = ValidationModule(llm, storage)
    report = module.validate_idea("p1")
    assert report.post_id == "p1"
    assert report.validation_verdict == "Go"
    
    md = module.format_report_markdown(report)
    assert "# Validation Report" in md

def test_monitor_module():
    scraper = MockScraper()
    llm = MockLLM()
    storage = MockStorage()
    discovery = DiscoveryModule(scraper, llm, storage)
    
    module = MonitorModule(discovery, storage)
    
    # Mocking scraper response to include a competitor name
    mock_scraper = MagicMock()
    mock_scraper.scrape.return_value = [
        ScrapedPost(
            id="m1", source="reddit", title="OpenAI is great", author="a", url="u", 
            upvotes=1, comments_count=1, created_at=datetime.now()
        )
    ]
    module.discovery.scraper = mock_scraper
    mentions = module.monitor_competitors(["sub1"], ["OpenAI"])
    assert mentions == 1
    assert "m1" in storage.signals

def test_leads_module():
    llm = MockLLM()
    storage = MockStorage()
    # Create a post with an intent keyword
    post = ScrapedPost(
        id="l1", source="reddit", title="I am looking for a tool", author="a", url="u", 
        upvotes=1, comments_count=1, created_at=datetime.now()
    )
    storage.save_post(post)
    
    module = LeadModule(llm, storage)
    leads = module.scan_for_leads()
    assert len(leads) > 0
    assert leads[0].intent_score == 0.8
