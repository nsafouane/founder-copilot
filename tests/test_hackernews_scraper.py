import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from copilot.providers.scrapers.hackernews import HackerNewsScraper
from copilot.models.schemas import ScrapedPost


@pytest.fixture
def mock_session():
    with patch("requests.Session") as mock:
        yield mock


def test_hackernews_scraper_name():
    scraper = HackerNewsScraper()
    assert scraper.name == "hackernews"


def test_hackernews_scraper_platform():
    scraper = HackerNewsScraper()
    assert scraper.platform == "Hacker News"


def test_hackernews_scraper_configure(mock_session):
    scraper = HackerNewsScraper()
    config = {"user_agent": "test_agent"}
    scraper.configure(config)
    assert scraper._session is not None


def test_hackernews_scraper_fetch_top_stories(mock_session):
    scraper = HackerNewsScraper()
    scraper.configure({})

    mock_instance = mock_session.return_value

    mock_instance.get.side_effect = [
        MagicMock(json=lambda: [123, 456, 789]),
        MagicMock(
            json=lambda: {
                "id": 123,
                "type": "story",
                "title": "Test Story",
                "by": "test_user",
                "score": 100,
                "time": 1609459200,
                "kids": [1, 2, 3],
                "descendants": 10,
                "url": "https://example.com/test",
            }
        ),
        MagicMock(
            json=lambda: {
                "id": 456,
                "type": "story",
                "title": "Ask HN: How to test",
                "by": "test_user2",
                "score": 50,
                "time": 1609459300,
                "kids": [],
                "descendants": 0,
            }
        ),
        MagicMock(
            json=lambda: {
                "id": 789,
                "type": "story",
                "title": "Show HN: New Tool",
                "by": "test_user3",
                "score": 75,
                "time": 1609459400,
                "kids": [4, 5],
                "descendants": 5,
                "url": "https://github.com/test/tool",
            }
        ),
    ]

    posts = scraper._fetch_stories("top", limit=3)

    assert len(posts) == 3
    assert all(isinstance(post, ScrapedPost) for post in posts)
    assert posts[0].id == "hn_123"
    assert posts[0].title == "Test Story"
    assert posts[0].source == "hackernews"
    assert posts[0].channel == "hn/story"
    assert posts[0].upvotes == 100
    assert posts[1].channel == "hn/ask"
    assert posts[2].channel == "hn/show"


def test_hackernews_scraper_skips_deleted(mock_session):
    scraper = HackerNewsScraper()
    scraper.configure({})

    mock_instance = mock_session.return_value

    mock_instance.get.side_effect = [
        MagicMock(json=lambda: [123, 456]),
        MagicMock(
            json=lambda: {
                "id": 123,
                "type": "story",
                "title": "Test Story",
                "by": "test_user",
                "score": 100,
                "time": 1609459200,
                "kids": [],
                "descendants": 0,
            }
        ),
        MagicMock(json=lambda: {"id": 456, "type": "story", "deleted": True}),
    ]

    posts = scraper._fetch_stories("top", limit=2)

    assert len(posts) == 1
    assert posts[0].id == "hn_123"


def test_hackernews_scraper_search_algolia(mock_session):
    scraper = HackerNewsScraper()
    scraper.configure({})

    mock_instance = mock_session.return_value

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "hits": [
            {
                "objectID": "999",
                "title": "Search Result",
                "author": "search_user",
                "points": 42,
                "num_comments": 15,
                "created_at_i": 1609459500,
                "url": "https://search.example.com",
                "_tags": ["story", "search"],
                "_highlightResult": {"title": {"value": "Search <em>Result</em>"}},
            }
        ]
    }
    mock_instance.get.return_value = mock_response

    posts = scraper._search_algolia("test query", limit=10)

    assert len(posts) == 1
    assert posts[0].id == "hn_999"
    assert posts[0].title == "Search Result"
    assert posts[0].source == "hackernews"
    assert posts[0].channel == "hn/story"
    assert posts[0].upvotes == 42
    assert posts[0].comments_count == 15


def test_hackernews_scraper_scrape_with_search(mock_session):
    scraper = HackerNewsScraper()
    scraper.configure({})

    mock_instance = mock_session.return_value

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "hits": [
            {
                "objectID": "888",
                "title": "Searched Story",
                "author": "user",
                "points": 25,
                "num_comments": 5,
                "created_at_i": 1609459600,
                "url": "https://example.com",
                "_tags": ["story"],
            }
        ]
    }
    mock_instance.get.return_value = mock_response

    posts = scraper.scrape("test query", limit=10, search=True)

    assert len(posts) == 1
    assert posts[0].id == "hn_888"


def test_hackernews_scraper_health_check_success(mock_session):
    scraper = HackerNewsScraper()
    scraper.configure({})

    mock_instance = mock_session.return_value
    mock_instance.get.return_value = MagicMock(status_code=200)

    assert scraper.health_check() is True


def test_hackernews_scraper_health_check_failure(mock_session):
    scraper = HackerNewsScraper()
    scraper.configure({})

    mock_instance = MagicMock()
    mock_session.return_value = mock_instance
    mock_instance.get.side_effect = Exception("Network error")

    assert scraper.health_check() is False


def test_hackernews_scraper_not_configured():
    scraper = HackerNewsScraper()
    with pytest.raises(RuntimeError, match="not configured"):
        scraper.scrape("ask")


def test_hackernews_item_to_post_mapping():
    scraper = HackerNewsScraper()

    item = {
        "id": 111,
        "type": "story",
        "title": "Ask HN: Best Python IDE?",
        "by": "python_user",
        "score": 88,
        "time": 1609459700,
        "kids": [1, 2],
        "descendants": 8,
        "text": "Looking for recommendations...",
    }

    post = scraper._item_to_post(item)

    assert post.id == "hn_111"
    assert post.title == "Ask HN: Best Python IDE?"
    assert post.author == "python_user"
    assert post.upvotes == 88
    assert post.comments_count == 2
    assert post.channel == "hn/ask"
    assert post.source == "hackernews"
    assert post.metadata["hn_id"] == 111
    assert post.metadata["hn_type"] == "story"


def test_hackernews_scraper_item_without_url():
    scraper = HackerNewsScraper()

    item = {
        "id": 222,
        "type": "story",
        "title": "Text-only post",
        "by": "user",
        "score": 10,
        "time": 1609459800,
        "kids": [],
        "descendants": 0,
        "text": "Some text content",
    }

    post = scraper._item_to_post(item)

    assert post.url == "https://news.ycombinator.com/item?id=222"
