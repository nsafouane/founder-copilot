import praw
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost


class RedditScraper(ScraperProvider):
    """Reddit scraper using PRAW."""

    def __init__(self):
        self._reddit: Optional[praw.Reddit] = None

    @property
    def name(self) -> str:
        return "reddit"

    @property
    def platform(self) -> str:
        return "Reddit"

    @property
    def capabilities(self) -> Set[ScraperCapability]:
        return {
            ScraperCapability.SEARCH,
            ScraperCapability.SORT_NEW,
            ScraperCapability.SORT_HOT,
            ScraperCapability.SORT_TOP,
            ScraperCapability.COMMENTS,
            ScraperCapability.HISTORICAL,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        self._reddit = praw.Reddit(
            client_id=config.get("client_id"),
            client_secret=config.get("client_secret"),
            user_agent=config.get("user_agent", "FounderCopilot/0.1"),
            username=config.get("username"),
            password=config.get("password"),
        )

    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        if not self._reddit:
            raise RuntimeError("RedditScraper not configured")

        subreddit = self._reddit.subreddit(target)
        posts = []

        sort = kwargs.get("sort", "new")
        if sort == "new":
            submissions = subreddit.new(limit=limit)
        elif sort == "hot":
            submissions = subreddit.hot(limit=limit)
        elif sort == "top":
            time_filter = kwargs.get("time_filter", "all")
            submissions = subreddit.top(limit=limit, time_filter=time_filter)
        else:
            submissions = subreddit.new(limit=limit)

        for sub in submissions:
            # Skip removed/deleted posts
            if (
                sub.removed_by_category
                or sub.selftext == "[removed]"
                or sub.selftext == "[deleted]"
            ):
                continue

            posts.append(
                ScrapedPost(
                    id=sub.id,
                    source="reddit",
                    title=sub.title,
                    body=sub.selftext if sub.is_self else None,
                    author=str(sub.author) if sub.author else "[deleted]",
                    url=f"https://reddit.com{sub.permalink}",
                    upvotes=sub.score,
                    comments_count=sub.num_comments,
                    created_at=datetime.fromtimestamp(sub.created_utc, tz=timezone.utc),
                    channel=f"r/{target}",
                    subreddit=target,
                    metadata={"upvote_ratio": sub.upvote_ratio, "is_self": sub.is_self},
                )
            )

        return posts
