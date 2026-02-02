import pytest
import json
from unittest.mock import MagicMock
from datetime import datetime
from copilot.modules.discovery import DiscoveryModule
from copilot.models.schemas import ScrapedPost, PainScore

@pytest.fixture
def mock_scraper():
    return MagicMock()

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.fixture
def discovery_module(mock_scraper, mock_llm):
    return DiscoveryModule(scraper=mock_scraper, llm=mock_llm)

def test_fetch_potential_pains(discovery_module, mock_scraper):
    mock_scraper.scrape.return_value = [
        ScrapedPost(
            id="1", source="reddit", title="Pain 1", author="user1", 
            url="url1", upvotes=10, comments_count=5, created_at=datetime.now()
        )
    ]
    
    posts = discovery_module.fetch_potential_pains(["test-sub"], limit_per_sub=10)
    
    assert len(posts) == 1
    assert posts[0].title == "Pain 1"
    mock_scraper.scrape.assert_called_once_with(source="reddit", target="test-sub", limit=10)

def test_analyze_pain_intensity(discovery_module, mock_llm):
    post = ScrapedPost(
        id="1", source="reddit", title="I hate manual data entry", body="It takes hours.",
        author="user1", url="url1", upvotes=10, comments_count=5, created_at=datetime.now()
    )
    
    pain_data = {
        "score": 0.9,
        "reasoning": "High frustration expressed.",
        "detected_problems": ["manual data entry"],
        "suggested_solutions": ["Automated data entry tool"]
    }
    mock_llm.complete.return_value = json.dumps(pain_data)
    
    score = discovery_module.analyze_pain_intensity(post)
    
    assert score.score == 0.9
    assert "manual data entry" in score.detected_problems
    mock_llm.complete.assert_called_once()

def test_discover_flow(discovery_module, mock_scraper, mock_llm):
    post1 = ScrapedPost(
        id="1", source="reddit", title="High Signal", author="user1", 
        url="url1", upvotes=100, comments_count=50, created_at=datetime.now()
    )
    post2 = ScrapedPost(
        id="2", source="reddit", title="Low Signal", author="user2", 
        url="url2", upvotes=1, comments_count=0, created_at=datetime.now()
    )
    
    mock_scraper.scrape.return_value = [post1, post2]
    
    pain_data = {
        "score": 0.85,
        "reasoning": "Good",
        "detected_problems": ["p1"],
        "suggested_solutions": ["s1"]
    }
    mock_llm.complete.return_value = json.dumps(pain_data)
    
    results = discovery_module.discover(["test-sub"])
    
    # post2 should be skipped by heuristic (upvotes/comments)
    assert len(results) == 1
    assert results[0][0].id == "1"
    assert results[0][1].score == 0.85
    assert results[0][1].engagement_score == 1.0  # (100*0.5 + 50*1.0)/100 = 1.0
    assert results[0][1].composite_value > 0.0

def test_analyze_pain_intensity_error(discovery_module, mock_llm):
    post = ScrapedPost(
        id="1", source="reddit", title="Test", author="user1", 
        url="url1", upvotes=10, comments_count=5, created_at=datetime.now()
    )
    mock_llm.complete.side_effect = Exception("API Error")
    
    score = discovery_module.analyze_pain_intensity(post)
    assert score.score == 0.0
    assert "Analysis failed" in score.reasoning

def test_fetch_potential_pains_error(discovery_module, mock_scraper):
    mock_scraper.scrape.side_effect = Exception("Scrape Error")
    posts = discovery_module.fetch_potential_pains(["test-sub"])
    assert len(posts) == 0
