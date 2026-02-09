from ..base import ScraperProvider, ScraperCapability
from .reddit import RedditScraper
from .hackernews import HackerNewsScraper
from .apify_g2 import ApifyG2Scraper
from .apify_capterra import ApifyCapterraScraper

__all__ = [
    "RedditScraper",
    "HackerNewsScraper",
    "ApifyG2Scraper",
    "ApifyCapterraScraper",
]
