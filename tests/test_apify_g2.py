import pytest
import sys
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone
from copilot.providers.scrapers.apify_g2 import ApifyG2Scraper
from copilot.models.schemas import ScrapedPost


def test_g2_scraper_name():
    scraper = ApifyG2Scraper()
    assert scraper.name == "g2"


def test_g2_scraper_platform():
    scraper = ApifyG2Scraper()
    assert scraper.platform == "G2"


def test_g2_scraper_configure():
    scraper = ApifyG2Scraper()
    config = {"apify_api_token": "test_token", "actor_id": "custom_actor"}
    scraper.configure(config)
    assert scraper._api_token == "test_token"
    assert scraper._actor_id == "custom_actor"


def test_g2_scraper_scrape():
    scraper = ApifyG2Scraper()
    scraper.configure({"apify_api_token": "test_token"})

    mock_actor = MagicMock()
    mock_dataset = MagicMock()

    mock_dataset.iterate_items.return_value = iter(
        [
            {
                "reviewId": "review123",
                "title": "Great product",
                "pros": "Easy to use",
                "cons": "Expensive",
                "reviewBody": "Overall good experience",
                "reviewerName": "John Doe",
                "reviewUrl": "https://www.g2.com/products/slack/reviews/123",
                "helpfulCount": 5,
                "starRating": 4,
                "reviewDate": "2024-01-15T10:30:00Z",
                "reviewerRole": "Manager",
                "companySize": "11-50",
                "industry": "Technology",
            }
        ]
    )

    mock_actor.call.return_value = {"defaultDatasetId": "dataset123"}

    mock_client_instance = MagicMock()
    mock_client_instance.actor.return_value = mock_actor
    mock_client_instance.dataset.return_value = mock_dataset

    mock_apify_client_class = MagicMock()
    mock_apify_client_class.return_value = mock_client_instance

    original_modules = sys.modules.copy()
    try:
        sys.modules["apify_client"] = MagicMock()
        sys.modules["apify_client"].ApifyClient = mock_apify_client_class

        posts = scraper.scrape("slack", limit=10)
    finally:
        sys.modules.clear()
        sys.modules.update(original_modules)

    assert len(posts) == 1
    assert isinstance(posts[0], ScrapedPost)
    assert posts[0].id == "g2_slack_review123"
    assert posts[0].source == "g2"
    assert posts[0].title == "Great product"
    assert "PROS: Easy to use" in posts[0].body
    assert "CONS: Expensive" in posts[0].body
    assert posts[0].author == "John Doe"
    assert posts[0].upvotes == 5
    assert posts[0].comments_count == 0
    assert posts[0].channel == "g2/slack"
    assert posts[0].metadata["star_rating"] == 4
    assert posts[0].metadata["pros"] == "Easy to use"
    assert posts[0].metadata["cons"] == "Expensive"
    assert posts[0].metadata["reviewer_role"] == "Manager"


def test_g2_scraper_scrape_with_star_filter():
    scraper = ApifyG2Scraper()
    scraper.configure({"apify_api_token": "test_token"})

    mock_actor = MagicMock()
    mock_dataset = MagicMock()
    mock_dataset.iterate_items.return_value = iter([])

    mock_actor.call.return_value = {"defaultDatasetId": "dataset123"}

    mock_client_instance = MagicMock()
    mock_client_instance.actor.return_value = mock_actor
    mock_client_instance.dataset.return_value = mock_dataset

    mock_apify_client_class = MagicMock()
    mock_apify_client_class.return_value = mock_client_instance

    original_modules = sys.modules.copy()
    try:
        sys.modules["apify_client"] = MagicMock()
        sys.modules["apify_client"].ApifyClient = mock_apify_client_class

        scraper.scrape("slack", limit=10, star_rating=1)
    finally:
        sys.modules.clear()
        sys.modules.update(original_modules)

    call_args = mock_actor.call.call_args[1]["run_input"]
    assert call_args["starRating"] == 1


def test_g2_scraper_combine_review_text():
    scraper = ApifyG2Scraper()

    item = {
        "pros": "Easy to use",
        "cons": "Expensive",
        "reviewBody": "Overall good",
    }
    text = scraper._combine_review_text(item)
    assert "PROS: Easy to use" in text
    assert "CONS: Expensive" in text
    assert "Overall good" in text


def test_g2_scraper_parse_date():
    scraper = ApifyG2Scraper()

    date_str = "2024-01-15T10:30:00Z"
    parsed = scraper._parse_date(date_str)
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 15
    assert parsed.tzinfo == timezone.utc


def test_g2_scraper_parse_date_invalid():
    scraper = ApifyG2Scraper()

    parsed = scraper._parse_date(None)
    assert isinstance(parsed, datetime)
    assert parsed.tzinfo == timezone.utc


def test_g2_scraper_not_configured():
    scraper = ApifyG2Scraper()
    with pytest.raises(RuntimeError, match="not configured"):
        scraper.scrape("slack")
