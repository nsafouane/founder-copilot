from typing import List, Dict, Any, Set, Optional
from datetime import datetime, timezone
from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost


class ApifyG2Scraper(ScraperProvider):
    """G2 review scraper using Apify Actor 'misceres/g2-product-scraper'."""

    def __init__(self):
        self._api_token: Optional[str] = None
        self._actor_id: str = "misceres/g2-product-scraper"

    @property
    def name(self) -> str:
        return "g2"

    @property
    def platform(self) -> str:
        return "G2"

    @property
    def capabilities(self) -> Set[ScraperCapability]:
        return {
            ScraperCapability.REVIEWS,
            ScraperCapability.SEARCH,
            ScraperCapability.SORT_NEW,
            ScraperCapability.HISTORICAL,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """Requires Apify API token."""
        self._api_token = config.get("apify_api_token") or config.get("api_token")
        self._actor_id = config.get("actor_id", "misceres/g2-product-scraper")

    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        """
        Scrape G2 reviews for a product.

        Args:
            target: G2 product slug (e.g., 'slack', 'notion')
            limit: Max reviews to return
            **kwargs:
                star_rating: Filter by star rating (1-5)
                sort: 'newest' | 'most_helpful'
        """
        if not self._api_token:
            raise RuntimeError("ApifyG2Scraper not configured. Missing API token.")

        from apify_client import ApifyClient

        client = ApifyClient(self._api_token)
        run_input = {
            "productUrl": f"https://www.g2.com/products/{target}/reviews",
            "maxReviews": limit,
            "sort": kwargs.get("sort", "newest"),
        }

        star_filter = kwargs.get("star_rating")
        if star_filter and 1 <= star_filter <= 5:
            run_input["starRating"] = star_filter

        run = client.actor(self._actor_id).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        posts = []
        for item in items[:limit]:
            review_id = item.get("reviewId", item.get("id", ""))
            posts.append(
                ScrapedPost(
                    id=f"g2_{target}_{review_id}",
                    source="g2",
                    title=item.get("title", f"G2 Review of {target}"),
                    body=self._combine_review_text(item),
                    author=item.get("reviewerName", "anonymous"),
                    url=item.get(
                        "reviewUrl", f"https://www.g2.com/products/{target}/reviews"
                    ),
                    upvotes=item.get("helpfulCount", 0),
                    comments_count=0,
                    created_at=self._parse_date(item.get("reviewDate")),
                    channel=f"g2/{target}",
                    metadata={
                        "star_rating": item.get("starRating", 0),
                        "pros": item.get("pros", ""),
                        "cons": item.get("cons", ""),
                        "reviewer_role": item.get("reviewerRole", ""),
                        "company_size": item.get("companySize", ""),
                        "industry": item.get("industry", ""),
                        "review_source": "g2",
                        "product_slug": target,
                    },
                )
            )
        return posts

    def _combine_review_text(self, item: dict) -> str:
        parts = []
        if item.get("pros"):
            parts.append(f"PROS: {item['pros']}")
        if item.get("cons"):
            parts.append(f"CONS: {item['cons']}")
        if item.get("reviewBody"):
            parts.append(item["reviewBody"])
        return "\n\n".join(parts)

    def _parse_date(self, date_str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)
