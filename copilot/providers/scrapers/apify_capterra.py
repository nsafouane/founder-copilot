from typing import List, Dict, Any, Set, Optional
from datetime import datetime, timezone
from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost


class ApifyCapterraScraper(ScraperProvider):
    """Capterra review scraper using Apify Actor 'apify/capterra-reviews-scraper'."""

    def __init__(self):
        self._api_token: Optional[str] = None
        self._actor_id: str = "apify/capterra-reviews-scraper"

    @property
    def name(self) -> str:
        return "capterra"

    @property
    def platform(self) -> str:
        return "Capterra"

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
        self._actor_id = config.get("actor_id", "apify/capterra-reviews-scraper")

    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        """
        Scrape Capterra reviews for a product.

        Args:
            target: Capterra product URL slug (e.g., product name)
            limit: Max reviews to return
            **kwargs:
                sort: 'newest' | 'oldest' | 'highest_rated' | 'lowest_rated'
        """
        if not self._api_token:
            raise RuntimeError(
                "ApifyCapterraScraper not configured. Missing API token."
            )

        from apify_client import ApifyClient

        client = ApifyClient(self._api_token)
        run_input = {
            "productUrl": target,
            "maxReviews": limit,
            "sort": kwargs.get("sort", "newest"),
        }

        run = client.actor(self._actor_id).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        posts = []
        for item in items[:limit]:
            review_id = item.get("id", item.get("reviewId", ""))
            product_name = item.get("productName", target)

            posts.append(
                ScrapedPost(
                    id=f"capterra_{product_name}_{review_id}",
                    source="capterra",
                    title=item.get("title", f"Capterra Review of {product_name}"),
                    body=self._combine_review_text(item),
                    author=item.get("reviewerName", "anonymous"),
                    url=item.get("reviewUrl", target),
                    upvotes=item.get("helpfulCount", item.get("votes", 0)),
                    comments_count=0,
                    created_at=self._parse_date(
                        item.get("date", item.get("reviewDate"))
                    ),
                    channel=f"capterra/{product_name}",
                    metadata={
                        "star_rating": item.get("overallRating", item.get("rating", 0)),
                        "ease_of_use": item.get("easeOfUse", 0),
                        "customer_service": item.get("customerService", 0),
                        "functionality": item.get("functionality", 0),
                        "value_for_money": item.get("valueForMoney", 0),
                        "pros": item.get("pros", ""),
                        "cons": item.get("cons", ""),
                        "reviewer_title": item.get("reviewerTitle", ""),
                        "company_size": item.get("companySize", ""),
                        "industry": item.get("industry", ""),
                        "review_source": "capterra",
                        "product_name": product_name,
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
        if item.get("comments"):
            parts.append(f"COMMENTS: {item['comments']}")
        return "\n\n".join(parts)

    def _parse_date(self, date_str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(date_str))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)
