import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional, Union, Dict
from ..providers.base import ScraperProvider, LLMProvider
from ..providers.storage.base import StorageProvider
from ..models.schemas import ScrapedPost, PainScore
from ..core.config import ConfigManager, SAAS_INTENT_KEYWORDS

SENTIMENT_SCORES = {
    "frustrated": 0.7,
    "desperate": 1.0,
    "curious": 0.4,
    "neutral": 0.2,
    "positive": 0.1,
}

logger = logging.getLogger(__name__)


class DiscoveryModule:
    """Core logic for finding and classifying high-signal pain points.

    Supports both single and multiple scrapers for multi-target discovery.
    """

    def __init__(
        self,
        scraper: Union[ScraperProvider, List[ScraperProvider]],
        llm: LLMProvider,
        storage: Optional[StorageProvider] = None,
    ):
        if isinstance(scraper, list):
            self.scrapers = scraper
        else:
            self.scrapers = [scraper]
        self.llm = llm
        self.storage = storage
        self.config = ConfigManager()
        self.llm_request_delay = float(self.config.get("llm_request_delay", 2))

        if self.storage:
            self.storage.initialize()

    @property
    def scraper(self) -> ScraperProvider:
        """Backward compatibility: returns the first scraper."""
        return self.scrapers[0]

    @scraper.setter
    def scraper(self, value: ScraperProvider) -> None:
        """Backward compatibility: replaces the first scraper."""
        if self.scrapers:
            self.scrapers[0] = value
        else:
            self.scrapers.append(value)

    def _passes_prefilter(self, post: ScrapedPost) -> bool:
        """Platform-aware heuristic filtering before LLM."""
        if post.source == "reddit":
            return post.upvotes >= 5 or post.comments_count >= 2
        elif post.source == "hackernews":
            return post.upvotes >= 3 or post.comments_count >= 1
        return True

    def fetch_potential_pains(
        self, targets: List[str] | Dict[str, List[str]], limit_per_target: int = 50
    ) -> List[ScrapedPost]:
        """Fetch posts from multiple sources and targets.

        Args:
            targets: Either a list of subreddit names (legacy) or a dict mapping
                     scraper names to lists of targets: {scraper_name: [target1, ...]}
            limit_per_target: Maximum items to fetch per target
        """
        all_posts = []

        if isinstance(targets, list):
            for sub in targets:
                for scraper in self.scrapers:
                    try:
                        posts = scraper.scrape(target=sub, limit=limit_per_target)
                        all_posts.extend(posts)
                    except Exception as e:
                        logger.error(f"Error scraping r/{sub} with {scraper.name}: {e}")
        else:
            for scraper in self.scrapers:
                scraper_targets = targets.get(scraper.name, [])
                for target in scraper_targets:
                    try:
                        posts = scraper.scrape(target=target, limit=limit_per_target)
                        all_posts.extend(posts)
                    except Exception as e:
                        logger.error(f"Error scraping {scraper.name}/{target}: {e}")

        return all_posts

    def analyze_pain_intensity(self, post: ScrapedPost) -> PainScore:
        """Use LLM to analyze the intensity of the pain point described in a post."""

        prompt = f"""
        Analyze the following social media post to determine if it expresses a 'pain point' (a problem, frustration, or unmet need).

        Title: {post.title}
        Body: {post.body or "N/A"}

        Return a JSON object with:
        - score: A float between 0.0 and 1.0 (0 = no pain, 1 = high intensity/frequent problem)
        - reasoning: A brief explanation of why you gave this score.
        - detected_problems: A list of strings identifying specific problems.
        - suggested_solutions: A list of strings (not objects) describing potential solutions.
        - validation_score: A float between 0.0 and 1.0 (How much validation/evidence of need is in the post?)
        - sentiment_label: One of "frustrated", "desperate", "curious", "neutral", "positive"
        - sentiment_intensity: A float between 0.0 and 1.0 indicating emotional intensity (0.0 = casual mention, 0.5 = clear frustration, 0.8 = desperate/urgent, 1.0 = business-critical)
        """

        system_prompt = "You are an expert product researcher specializing in identifying high-signal founder opportunities from social signals. You output strictly valid JSON."

        try:
            time.sleep(self.llm_request_delay)  # Added delay before LLM call
            response_text = self.llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
            )

            data = json.loads(response_text)

            sentiment_label = data.get("sentiment_label")
            sentiment_intensity = data.get("sentiment_intensity", 0.0)

            if sentiment_intensity > 0 and not sentiment_label:
                if sentiment_intensity >= 0.8:
                    sentiment_label = "desperate"
                elif sentiment_intensity >= 0.6:
                    sentiment_label = "frustrated"
                elif sentiment_intensity >= 0.4:
                    sentiment_label = "curious"
                else:
                    sentiment_label = "neutral"

            if sentiment_label and sentiment_intensity == 0.0:
                sentiment_intensity = SENTIMENT_SCORES.get(sentiment_label, 0.5)

            data["sentiment_label"] = sentiment_label
            data["sentiment_intensity"] = sentiment_intensity

            return PainScore(**data)
        except Exception as e:
            logger.error(f"Error analyzing post {post.id}: {e}")
            return PainScore(score=0.0, reasoning=f"Analysis failed: {str(e)}")

    def calculate_engagement_score(self, post: ScrapedPost) -> float:
        """Calculate engagement score (0-1) based on upvotes and comments."""
        # Heuristic: 100 upvotes + 50 comments = 1.0
        score = (post.upvotes * 0.5 + post.comments_count * 1.0) / 100.0
        return min(1.0, score)

    def calculate_recency_score(self, post: ScrapedPost) -> float:
        """Calculate recency score (0-1)."""
        now = datetime.now(timezone.utc)

        # Ensure post.created_at is timezone aware
        created_at = post.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        delta = now - created_at
        days = delta.days

        if days < 1:
            return 1.0
        if days < 7:
            return 0.8
        if days < 30:
            return 0.5
        if days < 90:
            return 0.2
        return 0.0

    def discover(
        self,
        subreddits_or_targets: List[str] | Dict[str, List[str]],
        min_score: float = 0.5,
    ) -> List[tuple[ScrapedPost, PainScore]]:
        """Run full discovery pipeline: scrape -> analyze -> filter.

        Supports both legacy (list of subreddits) and new (dict of targets) formats.
        """
        posts = self.fetch_potential_pains(subreddits_or_targets)
        results = []

        for post in posts:
            if not self._passes_prefilter(post):
                continue

            pain_info = self.analyze_pain_intensity(post)

            # Calculate composite metrics
            pain_info.engagement_score = self.calculate_engagement_score(post)
            pain_info.recency_score = self.calculate_recency_score(post)

            # Formula: Value = (Pain * 0.4) + (Engagement * 0.25) + (Validation * 0.25) + (Recency * 0.10)
            pain_info.composite_value = (
                (pain_info.score * 0.4)
                + (pain_info.engagement_score * 0.25)
                + (pain_info.validation_score * 0.25)
                + (pain_info.recency_score * 0.10)
            )

            if pain_info.composite_value >= min_score:
                results.append((post, pain_info))

                # Persist to storage if available
                if self.storage:
                    try:
                        self.storage.save_post(post)
                        self.storage.save_signal(post.id, pain_info)
                    except Exception as e:
                        logger.error(f"Error saving to storage: {e}")

        # Sort by composite value descending
        results.sort(key=lambda x: x[1].composite_value, reverse=True)
        return results
