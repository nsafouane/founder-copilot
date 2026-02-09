import pytest
import sys
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone
from copilot.providers.scrapers.apify_capterra import ApifyCapterraScraper
from copilot.models.schemas import ScrapedPost


def test_capterra_scraper_name():
    scraper = ApifyCapterraScraper()
    assert scraper.name == "capterra"


def test_capterra_scraper_platform():
    scraper = ApifyCapterraScraper()
    assert scraper.platform == "Capterra"


def test_capterra_scraper_configure():
    scraper = ApifyCapterraScraper()
    config = {"apify_api_token": "test_token", "actor_id": "custom_actor"}
    scraper.configure(config)
    assert scraper._api_token == "test_token"
    assert scraper._actor_id == "custom_actor"


def test_capterra_scraper_scrape():
    scraper = ApifyCapterraScraper()
    scraper.configure({"apify_api_token": "test_token"})

    mock_actor = MagicMock()
    mock_dataset = MagicMock()

    mock_dataset.iterate_items.return_value = iter(
        [
            {
                "id": "review123",
                "title": "Excellent software",
                "pros": "Intuitive interface",
                "cons": "Limited features in free version",
                "reviewBody": "Love using it daily",
                "reviewerName": "Jane Smith",
                "reviewUrl": "https://www.capterra.com/slack",
                "votes": 8,
                "overallRating": 5,
                "easeOfUse": 5,
                "customerService": 4,
                "functionality": 4,
                "valueForMoney": 4,
                "date": "2024-02-20T14:45:00Z",
                "reviewerTitle": "CTO",
                "companySize": "51-200",
                "industry": "Software",
                "productName": "slack",
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

        posts = scraper.scrape("https://www.capterra.com/slack", limit=10)
    finally:
        sys.modules.clear()
        sys.modules.update(original_modules)

    assert len(posts) == 1
    assert isinstance(posts[0], ScrapedPost)
    assert posts[0].id == "capterra_slack_review123"
    assert posts[0].source == "capterra"
    assert posts[0].title == "Excellent software"
    assert "PROS: Intuitive interface" in posts[0].body
    assert "CONS: Limited features in free version" in posts[0].body
    assert posts[0].author == "Jane Smith"
    assert posts[0].upvotes == 8
    assert posts[0].comments_count == 0
    assert posts[0].channel == "capterra/slack"
    assert posts[0].metadata["star_rating"] == 5
    assert posts[0].metadata["ease_of_use"] == 5
    assert posts[0].metadata["customer_service"] == 4
    assert posts[0].metadata["functionality"] == 4
    assert posts[0].metadata["value_for_money"] == 4
    assert posts[0].metadata["pros"] == "Intuitive interface"
    assert posts[0].metadata["cons"] == "Limited features in free version"
    assert posts[0].metadata["reviewer_title"] == "CTO"


def test_capterra_scraper_scrape_with_sort():
    scraper = ApifyCapterraScraper()
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

        scraper.scrape("https://www.capterra.com/slack", limit=10, sort="highest_rated")
    finally:
        sys.modules.clear()
        sys.modules.update(original_modules)

    call_args = mock_actor.call.call_args[1]["run_input"]
    assert call_args["sort"] == "highest_rated"


def test_capterra_scraper_combine_review_text():
    scraper = ApifyCapterraScraper()

    item = {
        "pros": "Intuitive interface",
        "cons": "Limited features",
        "reviewBody": "Love using it",
        "comments": "Would recommend to others",
    }
    text = scraper._combine_review_text(item)
    assert "PROS: Intuitive interface" in text
    assert "CONS: Limited features" in text
    assert "Love using it" in text
    assert "COMMENTS: Would recommend to others" in text


def test_capterra_scraper_parse_date():
    scraper = ApifyCapterraScraper()

    date_str = "2024-02-20T14:45:00Z"
    parsed = scraper._parse_date(date_str)
    assert parsed.year == 2024
    assert parsed.month == 2
    assert parsed.day == 20
    assert parsed.tzinfo == timezone.utc


def test_capterra_scraper_parse_date_invalid():
    scraper = ApifyCapterraScraper()

    parsed = scraper._parse_date(None)
    assert isinstance(parsed, datetime)
    assert parsed.tzinfo == timezone.utc


def test_capterra_scraper_not_configured():
    scraper = ApifyCapterraScraper()
    with pytest.raises(RuntimeError, match="not configured"):
        scraper.scrape("https://www.capterra.com/slack")


def test_capterra_scraper_missing_fields():
    scraper = ApifyCapterraScraper()
    scraper.configure({"apify_api_token": "test_token"})

    mock_actor = MagicMock()
    mock_dataset = MagicMock()

    mock_dataset.iterate_items.return_value = iter(
        [
            {
                "id": "review123",
                "title": "Test Review",
                "productName": "testproduct",
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

        posts = scraper.scrape("https://www.capterra.com/test", limit=10)
    finally:
        sys.modules.clear()
        sys.modules.update(original_modules)

    assert len(posts) == 1
    assert posts[0].upvotes == 0
    assert posts[0].metadata["star_rating"] == 0
    assert posts[0].author == "anonymous"
