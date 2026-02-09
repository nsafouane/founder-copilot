import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from pathlib import Path
from copilot.models.schemas import ScrapedPost, PainScore, Lead, ValidationReport
from copilot.modules.discovery import DiscoveryModule
from copilot.modules.validation import ValidationModule
from copilot.modules.monitor import MonitorModule
from copilot.modules.leads import LeadModule
from copilot.modules.export import ExportModule


class MockScraper:
    def scrape(self, target, limit=100, **kwargs):
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
                subreddit="test_sub",
                channel=f"r/{target}",
            )
            for i in range(limit)
        ]


class MockLLM:
    def complete(self, prompt, system_prompt=None, response_format=None):
        prompt_lower = prompt.lower()
        if "validation report" in prompt_lower or "validation verdict" in prompt_lower:
            return '{"idea_summary": "Test Idea", "market_size_estimate": "Big", "competitors": [], "swot_analysis": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}, "validation_verdict": "Go", "next_steps": []}'
        if "intent" in prompt_lower and "lead" in prompt_lower:
            return '{"intent_score": 0.8, "content_snippet": "Needs help", "reasoning": "Clear intent"}'
        return '{"score": 0.9, "reasoning": "High pain", "detected_problems": ["prob1"], "suggested_solutions": ["sol1"], "engagement_score": 0.7, "validation_score": 0.8, "recency_score": 0.9, "composite_value": 0.85}'


class MockStorage:
    def __init__(self):
        self.posts = []
        self.signals = {}
        self.leads = []
        self.reports = []

    def initialize(self):
        pass

    def save_post(self, post):
        self.posts.append(post)

    def save_signal(self, post_id, pain_info):
        self.signals[post_id] = pain_info

    def get_posts(self, limit=100):
        return self.posts

    def get_post_by_id(self, post_id):
        for post in self.posts:
            if post.id == post_id:
                return post
        raise ValueError(f"Post {post_id} not found")

    def save_lead(self, lead):
        self.leads.append(lead)

    def get_leads(self, limit=100):
        return self.leads

    def save_report(self, report):
        self.reports.append(report)

    def get_reports(self, limit=100):
        return self.reports


def test_validation_module():
    llm = MockLLM()
    storage = MockStorage()
    post = ScrapedPost(
        id="p1",
        source="reddit",
        title="Pain",
        author="a",
        url="u",
        upvotes=1,
        comments_count=1,
        created_at=datetime.now(),
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

    module = MonitorModule(discovery, llm, storage)

    # Mocking scraper response to include a competitor name
    mock_scraper = MagicMock()
    mock_scraper.scrape.return_value = [
        ScrapedPost(
            id="m1",
            source="reddit",
            title="OpenAI is great",
            author="a",
            url="u",
            upvotes=1,
            comments_count=1,
            created_at=datetime.now(),
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
        id="l1",
        source="reddit",
        title="I am looking for a tool",
        author="a",
        url="u",
        upvotes=1,
        comments_count=1,
        created_at=datetime.now(),
    )
    storage.save_post(post)

    module = LeadModule(llm, storage)
    leads = module.scan_for_leads()
    assert len(leads) > 0
    assert leads[0].intent_score == 0.8


def test_validation_module_missing_post():
    llm = MockLLM()
    storage = MockStorage()
    module = ValidationModule(llm, storage)
    with pytest.raises(ValueError, match="Post p99 not found"):
        module.validate_idea("p99")


def test_monitor_module_run_periodic_discovery():
    scraper = MockScraper()
    llm = MockLLM()
    storage = MockStorage()
    discovery = DiscoveryModule(scraper, llm, storage)
    module = MonitorModule(discovery, llm, storage)

    with patch("time.sleep"):
        count = module.run_periodic_discovery(["test_sub"], min_score=0.5)
    assert count >= 0


def test_monitor_module_deep_research_no_api_key():
    scraper = MockScraper()
    llm = MockLLM()
    storage = MockStorage()
    discovery = DiscoveryModule(scraper, llm, storage)

    with patch.object(discovery.config, "get", return_value=None):
        module = MonitorModule(discovery, llm, storage)

        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = [
            ScrapedPost(
                id="m1",
                source="reddit",
                title="OpenAI is great",
                author="a",
                url="u",
                upvotes=1,
                comments_count=1,
                created_at=datetime.now(),
            )
        ]
        module.discovery.scraper = mock_scraper
        mentions = module.monitor_competitors(["sub1"], ["OpenAI"])
        assert mentions == 1
        assert "m1" in storage.signals


def test_export_module_leads_to_csv():
    storage = MockStorage()

    lead1 = Lead(
        post_id="p1",
        author="user1",
        content_snippet="Needs tool",
        contact_url="http://example.com",
        intent_score=0.8,
        status="new",
        created_at=datetime.now(),
    )
    lead2 = Lead(
        post_id="p2",
        author="user2",
        content_snippet="Looking for solution",
        contact_url="http://example2.com",
        intent_score=0.9,
        status="contacted",
        created_at=datetime.now(),
    )
    storage.save_lead(lead1)
    storage.save_lead(lead2)

    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_leads_to_csv(temp_path)
        assert count == 2
        assert temp_path.exists()

        content = temp_path.read_text()
        assert "user1" in content
        assert "user2" in content
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_export_module_reports_to_csv():
    storage = MockStorage()

    report1 = ValidationReport(
        post_id="p1",
        idea_summary="Test idea 1",
        market_size_estimate="Large",
        competitors=[
            {"name": "Comp1", "url": "http://comp1.com", "description": "Competitor 1"}
        ],
        swot_analysis={
            "strengths": ["s1"],
            "weaknesses": ["w1"],
            "opportunities": ["o1"],
            "threats": ["t1"],
        },
        validation_verdict="Go",
        next_steps=["Step 1", "Step 2"],
        generated_at=datetime.now(),
    )
    report2 = ValidationReport(
        post_id="p2",
        idea_summary="Test idea 2",
        market_size_estimate="Medium",
        competitors=[],
        swot_analysis={
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        },
        validation_verdict="No-Go",
        next_steps=[],
        generated_at=datetime.now(),
    )
    storage.save_report(report1)
    storage.save_report(report2)

    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_reports_to_csv(temp_path)
        assert count == 2
        assert temp_path.exists()

        content = temp_path.read_text()
        assert "Test idea 1" in content
        assert "Test idea 2" in content
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_export_module_leads_to_md():
    storage = MockStorage()

    lead1 = Lead(
        post_id="p1",
        author="user1",
        content_snippet="Needs tool",
        contact_url="http://example.com",
        intent_score=0.8,
        status="new",
        created_at=datetime.now(),
    )
    storage.save_lead(lead1)

    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_leads_to_md(temp_path)
        assert count == 1
        assert temp_path.exists()

        content = temp_path.read_text()
        assert "# Potential Customer Leads" in content
        assert "user1" in content
        assert "Needs tool" in content
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_export_module_reports_to_md():
    storage = MockStorage()

    report1 = ValidationReport(
        post_id="p1",
        idea_summary="Test idea 1",
        market_size_estimate="Large",
        competitors=[
            {"name": "Comp1", "url": "http://comp1.com", "description": "Competitor 1"}
        ],
        swot_analysis={
            "strengths": ["s1"],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        },
        validation_verdict="Go",
        next_steps=["Step 1"],
        generated_at=datetime.now(),
    )
    storage.save_report(report1)

    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_reports_to_md(temp_path)
        assert count == 1
        assert temp_path.exists()

        content = temp_path.read_text()
        assert "# Validation Reports" in content
        assert "Test idea 1" in content
        assert "Go" in content
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_export_module_empty_leads_csv():
    storage = MockStorage()
    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_leads_to_csv(temp_path)
        assert count == 0
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_export_module_empty_reports_csv():
    storage = MockStorage()
    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_reports_to_csv(temp_path)
        assert count == 0
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_export_module_empty_leads_md():
    storage = MockStorage()
    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_leads_to_md(temp_path)
        assert count == 0
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_export_module_empty_reports_md():
    storage = MockStorage()
    export = ExportModule(storage)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        temp_path = Path(f.name)

    try:
        count = export.export_reports_to_md(temp_path)
        assert count == 0
    finally:
        if temp_path.exists():
            temp_path.unlink()
