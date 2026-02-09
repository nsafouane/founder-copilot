"""
IndieHackers Scraper for Founder Co-Pilot

Fetches "Product Ideas" and "Validation Stories" from indiehackers.com
No official API exists - uses RSS/HTML scraping.
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import requests

from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost

logger = logging.getLogger("IndieHackersScraper")

BASE_URL = "https://www.indiehackers.com"
USER_AGENT = "FounderCopilot/1.2"

class IndieHackersScraper(ScraperProvider):
    """IndieHackers.com scraper for product ideas and validation stories."""

    def __init__(self):
        self._session = None

    @property
    def name(self) -> str:
        return "indiehackers"

    @property
    def platform(self) -> str:
        return "Indie Hackers"

    @property
    def capabilities(self) -> set[ScraperCapability]:
        return {
            ScraperCapability.SEARCH,
            ScraperCapability.COMMENTS,
            ScraperCapability.HISTORICAL,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": config.get("user_agent", USER_AGENT)
        })

    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        """
        Scrape posts from IndieHackers.

        Args:
            target: Search query or 'newest' for latest
            limit: Maximum items to return
            **kwargs: 'page' for pagination

        Returns:
            List of ScrapedPost
        """
        if not self._session:
            raise RuntimeError("IndieHackersScraper not configured")

        # Default to homepage if no target
        if not target:
            target = "newest"

        url = f"{BASE_URL}/"
        if target != "newest":
            url = f"{BASE_URL}/{target}"

        logger.info(f"Fetching IndieHackers: {url}")

        try:
            resp = self._session.get(url, timeout=30)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')

            posts = []
            
            # Try to extract posts from the main feed
            # IndieHackers has posts with upvotes, comments, and metadata
            article_elements = soup.find_all('article', class_=lambda c: 'border' in c.get('class', ''))
            
            for article in article_elements[:limit]:
                post_data = self._extract_post(article)
                if post_data:
                    posts.append(post_data)

            logger.info(f"Scraped {len(posts)} posts from IndieHackers")
            return posts

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return []

    def _extract_post(self, article) -> ScrapedPost:
        """Extract post data from an article element."""
        try:
            # Find title (usually in a header)
            header = article.find(['h1', 'h2', 'h3', 'h4'], class_=lambda c: c.get('class', '').lower())
            
            if header:
                title = header.get_text(strip=True)
            else:
                title = article.find('a', class_=lambda c: 'title' in c.get('class', '')).get_text(strip=True)
            
            if not title:
                title = "Untitled"

            # Find body/content
            body_div = article.find('div', class_=lambda c: 'content' in c.get('class', ''))
            if body_div:
                body = body_div.get_text(separator=' ', strip=True)[:500]  # Truncate long content
            else:
                body = ""

            # Find link
            link_elem = article.find('a')
            url = link_elem['href'] if link_elem else f"{BASE_URL}/post/{article.get('id', '')}" if article.get('id') else BASE_URL

            # Find author
            author_span = article.find('span', class_=lambda c: 'author' in c.get('class', ''))
            author = author_span.get_text(strip=True) if author_span else "Indie Hacker"

            # Find upvotes
            upvotes = 0
            votes_elem = article.find(['span', 'div'], string=re.compile(r'(\d+)\s*votes?', re.IGNORECASE))
            if votes_elem:
                votes_text = votes_elem.get_text()
                # Extract number from text like "123 votes"
                match = re.search(r'(\d+)', votes_text)
                if match:
                    upvotes = int(match.group(1))

            # Find comments count
            comments_count = 0
            comments_elem = article.find(['span', 'a'], class_=lambda c: 'comment' in c.get('class', ''))
            if comments_elem:
                comments_text = comments_elem.get_text()
                match = re.search(r'(\d+)', comments_text)
                if match:
                    comments_count = int(match.group(1))

            # Extract timestamp if available
            time_elem = article.find('time')
            if time_elem and time_elem.get('datetime'):
                try:
                    created_at = datetime.fromisoformat(time_elem['datetime'])
                except:
                    created_at = datetime.now(timezone.utc)
            else:
                created_at = datetime.now(timezone.utc)

            return ScrapedPost(
                id=f"ih_{article.get('id', '')}" if article.get('id') else f"ih_{hash(title) % 10**12}",
                source="indiehackers",
                title=title,
                body=body,
                author=author,
                url=url,
                upvotes=upvotes,
                comments_count=comments_count,
                created_at=created_at,
                channel="indiehackers",
                metadata={
                    "indiehackers_id": article.get("id", ""),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Post extraction failed: {e}")
            return None

    def health_check(self) -> bool:
        try:
            if not self._session:
                return False
            resp = self._session.get(f"{BASE_URL}/newest", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
