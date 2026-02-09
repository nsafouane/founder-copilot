import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost

HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA = "https://hn.algolia.com/api/v1"


class HackerNewsScraper(ScraperProvider):
    """Hacker News scraper using Firebase API (stories) + Algolia (search)."""

    def __init__(self):
        self._session: requests.Session | None = None

    @property
    def name(self) -> str:
        return "hackernews"

    @property
    def platform(self) -> str:
        return "Hacker News"

    @property
    def capabilities(self) -> Set[ScraperCapability]:
        return {
            ScraperCapability.SEARCH,
            ScraperCapability.SORT_NEW,
            ScraperCapability.SORT_TOP,
            ScraperCapability.COMMENTS,
            ScraperCapability.HISTORICAL,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": config.get("user_agent", "FounderCopilot/1.1")}
        )

    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        if not self._session:
            raise RuntimeError("HackerNewsScraper not configured")

        if kwargs.get("search", False):
            return self._search_algolia(query=target, limit=limit, **kwargs)
        else:
            return self._fetch_stories(feed=target, limit=limit)

    def _fetch_stories(self, feed: str, limit: int) -> List[ScrapedPost]:
        feed_map = {
            "top": "topstories",
            "new": "newstories",
            "ask": "askstories",
            "show": "showstories",
            "jobs": "jobstories",
        }
        endpoint = feed_map.get(feed, feed)

        resp = self._session.get(f"{HN_BASE}/{endpoint}.json")
        resp.raise_for_status()
        story_ids = resp.json()[:limit]

        posts = []
        for sid in story_ids:
            try:
                item_resp = self._session.get(f"{HN_BASE}/item/{sid}.json")
                item_resp.raise_for_status()
                item = item_resp.json()
                if item and item.get("type") == "story" and not item.get("deleted"):
                    posts.append(self._item_to_post(item))
            except Exception:
                continue
        return posts

    def _search_algolia(self, query: str, limit: int, **kwargs) -> List[ScrapedPost]:
        sort = kwargs.get("sort", "new")
        endpoint = "search" if sort == "top" else "search_by_date"

        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": min(limit, 1000),
        }
        resp = self._session.get(f"{HN_ALGOLIA}/{endpoint}", params=params)
        resp.raise_for_status()

        posts = []
        for hit in resp.json().get("hits", []):
            posts.append(
                ScrapedPost(
                    id=f"hn_{hit['objectID']}",
                    source="hackernews",
                    title=hit.get("title", ""),
                    body=hit.get("story_text") or hit.get("comment_text"),
                    author=hit.get("author", "unknown"),
                    url=hit.get("url")
                    or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                    upvotes=hit.get("points", 0) or 0,
                    comments_count=hit.get("num_comments", 0) or 0,
                    created_at=datetime.fromtimestamp(
                        hit.get("created_at_i", 0), tz=timezone.utc
                    ),
                    channel=f"hn/{hit.get('_tags', ['story'])[0]}",
                    metadata={
                        "hn_id": hit["objectID"],
                        "relevancy_score": hit.get("_highlightResult", {}),
                    },
                )
            )
        return posts

    def _item_to_post(self, item: dict) -> ScrapedPost:
        title = item.get("title", "")
        if title.startswith("Ask HN"):
            channel = "hn/ask"
        elif title.startswith("Show HN"):
            channel = "hn/show"
        else:
            channel = "hn/story"

        return ScrapedPost(
            id=f"hn_{item['id']}",
            source="hackernews",
            title=title,
            body=item.get("text"),
            author=item.get("by", "unknown"),
            url=item.get("url") or f"https://news.ycombinator.com/item?id={item['id']}",
            upvotes=item.get("score", 0),
            comments_count=len(item.get("kids", [])),
            created_at=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc),
            channel=channel,
            metadata={
                "hn_id": item["id"],
                "hn_type": item.get("type"),
                "descendants": item.get("descendants", 0),
            },
        )

    def health_check(self) -> bool:
        try:
            if not self._session:
                return False
            resp = self._session.get(f"{HN_BASE}/topstories.json", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
