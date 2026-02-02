import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from copilot.providers.reddit_scraper import RedditScraper
from copilot.models.schemas import ScrapedPost

@pytest.fixture
def mock_reddit():
    with patch("praw.Reddit") as mock:
        yield mock

def test_reddit_scraper_name():
    scraper = RedditScraper()
    assert scraper.name == "reddit"

def test_reddit_scraper_configure(mock_reddit):
    scraper = RedditScraper()
    config = {
        "client_id": "test_id",
        "client_secret": "test_secret",
        "user_agent": "test_agent"
    }
    scraper.configure(config)
    mock_reddit.assert_called_once_with(
        client_id="test_id",
        client_secret="test_secret",
        user_agent="test_agent",
        username=None,
        password=None
    )

def test_reddit_scraper_scrape(mock_reddit):
    scraper = RedditScraper()
    scraper.configure({})
    
    # Mock the subreddit and submissions
    mock_sub = MagicMock()
    mock_reddit.return_value.subreddit.return_value = mock_sub
    
    mock_submission = MagicMock()
    mock_submission.id = "123"
    mock_submission.title = "Test Title"
    mock_submission.selftext = "Test Body"
    mock_submission.author = "test_user"
    mock_submission.permalink = "/r/test/comments/123"
    mock_submission.score = 10
    mock_submission.num_comments = 5
    mock_submission.created_utc = 1609459200.0  # 2021-01-01
    mock_submission.is_self = True
    mock_submission.removed_by_category = None
    mock_submission.upvote_ratio = 0.9
    
    mock_sub.new.return_value = [mock_submission]
    
    posts = scraper.scrape("reddit", "test_sub", limit=1)
    
    assert len(posts) == 1
    assert isinstance(posts[0], ScrapedPost)
    assert posts[0].id == "123"
    assert posts[0].title == "Test Title"
    assert posts[0].body == "Test Body"
    assert posts[0].author == "test_user"
    assert posts[0].upvotes == 10
    assert posts[0].subreddit == "test_sub"

def test_reddit_scraper_scrape_skips_removed(mock_reddit):
    scraper = RedditScraper()
    scraper.configure({})
    
    mock_sub = MagicMock()
    mock_reddit.return_value.subreddit.return_value = mock_sub
    
    mock_submission = MagicMock()
    mock_submission.removed_by_category = "deleted"
    
    mock_sub.new.return_value = [mock_submission]
    
    posts = scraper.scrape("reddit", "test_sub", limit=1)
    assert len(posts) == 0
