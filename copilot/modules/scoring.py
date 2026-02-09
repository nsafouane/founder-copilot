import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Optional
from ..models.schemas import ScrapedPost, PainScore, OpportunityScore
from ..providers.storage.base import StorageProvider
from ..core.config import SAAS_INTENT_KEYWORDS

logger = logging.getLogger(__name__)

WEIGHTS = {
    "pain_intensity": 0.25,
    "engagement_norm": 0.15,
    "validation_evidence": 0.15,
    "sentiment_intensity": 0.15,
    "recency": 0.08,
    "trend_momentum": 0.12,
    "market_signal": 0.10,
}

ENGAGEMENT_NORMALIZERS = {
    "reddit": {
        "upvote_cap": 200,
        "upvote_weight": 0.5,
        "comment_cap": 50,
        "comment_weight": 0.5,
    },
    "hackernews": {
        "upvote_cap": 300,
        "upvote_weight": 0.6,
        "comment_cap": 150,
        "comment_weight": 0.4,
    },
    "g2": {
        "upvote_cap": 20,
        "upvote_weight": 0.3,
        "comment_cap": 1,
        "comment_weight": 0.0,
        "star_rating_weight": 0.7,
    },
    "capterra": {
        "upvote_cap": 15,
        "upvote_weight": 0.2,
        "comment_cap": 1,
        "comment_weight": 0.0,
        "star_rating_weight": 0.8,
    },
}

SENTIMENT_SCORES = {
    "frustrated": 0.7,
    "desperate": 1.0,
    "curious": 0.4,
    "neutral": 0.2,
    "positive": 0.1,
}


def calculate_engagement_norm(post: ScrapedPost) -> float:
    """Normalize engagement to 0-1 regardless of source."""
    norms = ENGAGEMENT_NORMALIZERS.get(post.source, ENGAGEMENT_NORMALIZERS["reddit"])

    upvote_score = min(1.0, post.upvotes / norms["upvote_cap"]) * norms["upvote_weight"]
    comment_score = (
        min(1.0, post.comments_count / max(1, norms["comment_cap"]))
        * norms["comment_weight"]
    )

    star_weight = norms.get("star_rating_weight", 0.0)
    if star_weight > 0 and "star_rating" in post.metadata:
        star_pain = max(0.0, (5 - post.metadata["star_rating"]) / 4.0)
        return upvote_score + comment_score + (star_pain * star_weight)

    return upvote_score + comment_score


def calculate_recency_score(post: ScrapedPost) -> float:
    """Calculate recency score (0-1)."""
    now = datetime.now(timezone.utc)

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


def extract_key_terms(post: ScrapedPost) -> List[str]:
    """Extract key terms from post title and body using simple frequency analysis."""
    content = f"{post.title} {post.body or ''}".lower()

    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "dare",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
        "this",
        "that",
        "these",
        "those",
        "am",
        "and",
        "or",
        "but",
        "if",
        "because",
        "as",
        "until",
        "while",
        "of",
        "at",
        "by",
        "for",
        "with",
        "about",
        "against",
        "between",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "to",
        "from",
        "up",
        "down",
        "in",
        "out",
        "on",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "any",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "also",
        "now",
        "what",
        "which",
        "who",
        "whom",
        "like",
        "get",
        "got",
        "getting",
        "go",
        "goes",
        "going",
        "want",
        "wants",
        "make",
        "makes",
        "use",
        "uses",
        "using",
        "see",
        "seen",
        "saw",
        "think",
        "thinks",
        "thinking",
    }

    words = []
    for word in content.split():
        cleaned = "".join(c for c in word if c.isalnum())
        if len(cleaned) >= 3 and cleaned not in stop_words:
            words.append(cleaned)

    from collections import Counter

    word_freq = Counter(words)

    return [word for word, _ in word_freq.most_common(5)]


def calculate_trend_momentum(post: ScrapedPost, storage: StorageProvider) -> float:
    """Calculate trend momentum: are similar pain topics increasing over time?"""
    try:
        key_terms = extract_key_terms(post)
        if not key_terms:
            return 0.5

        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(days=30)
        older_cutoff_start = now - timedelta(days=60)
        older_cutoff_end = now - timedelta(days=30)

        recent_posts = storage.get_posts(limit=1000, source=post.source)
        recent_count = 0
        older_count = 0

        for p in recent_posts:
            if p.id == post.id:
                continue

            content = f"{p.title} {p.body or ''}".lower()
            if any(term.lower() in content for term in key_terms):
                if p.created_at >= recent_cutoff:
                    recent_count += 1
                elif older_cutoff_start <= p.created_at < older_cutoff_end:
                    older_count += 1

        if older_count == 0:
            if recent_count == 0:
                return 0.5
            return 0.5  # New topic with some data, moderate momentum

        ratio = recent_count / older_count
        return 1.0 / (1.0 + math.exp(-2 * (ratio - 1.0)))
    except Exception as e:
        logger.error(f"Error calculating trend momentum for post {post.id}: {e}")
        return 0.5


def calculate_market_signal(post: ScrapedPost) -> float:
    """Calculate market signal score based on SaaS intent keywords."""
    content = f"{post.title} {post.body or ''}".lower()
    score = 0.0

    for level, keywords in SAAS_INTENT_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw.lower() in content)
        if level == "high":
            score += matches * 0.3
        elif level == "medium":
            score += matches * 0.15
        else:
            score += matches * 0.05

    return min(1.0, score)


def calculate_cross_source_bonus(post: ScrapedPost, storage: StorageProvider) -> float:
    """Bonus for pain topics confirmed across multiple platforms."""
    try:
        key_terms = extract_key_terms(post)
        if not key_terms:
            return 0.0

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=90)

        all_posts = storage.get_posts(limit=1000)
        sources_with_matches: Set[str] = set()

        for p in all_posts:
            if p.created_at < cutoff:
                continue

            if p.source == post.source:
                continue

            content = f"{p.title} {p.body or ''}".lower()
            if any(term.lower() in content for term in key_terms):
                sources_with_matches.add(p.source)

        additional_sources = len(sources_with_matches)
        return additional_sources * 0.05
    except Exception as e:
        logger.error(f"Error calculating cross-source bonus for post {post.id}: {e}")
        return 0.0


def compute_opportunity_score(
    post: ScrapedPost,
    pain: PainScore,
    storage: StorageProvider,
    weights: Optional[Dict[str, float]] = None,
) -> OpportunityScore:
    """Compute the unified Opportunity Score for a post + its pain analysis."""
    if weights is None:
        weights = WEIGHTS.copy()

    d1 = pain.score
    d2 = calculate_engagement_norm(post)
    d3 = pain.validation_score
    d4 = pain.sentiment_intensity
    d5 = calculate_recency_score(post)
    d6 = calculate_trend_momentum(post, storage)
    d7 = calculate_market_signal(post)

    base_score = (
        weights["pain_intensity"] * d1
        + weights["engagement_norm"] * d2
        + weights["validation_evidence"] * d3
        + weights["sentiment_intensity"] * d4
        + weights["recency"] * d5
        + weights["trend_momentum"] * d6
        + weights["market_signal"] * d7
    )

    cross_bonus = calculate_cross_source_bonus(post, storage)

    final_score = min(1.0, base_score + cross_bonus)

    dimensions = {
        "pain_intensity": d1,
        "engagement_norm": d2,
        "validation_evidence": d3,
        "sentiment_intensity": d4,
        "recency": d5,
        "trend_momentum": d6,
        "market_signal": d7,
    }

    return OpportunityScore(
        post_id=post.id,
        source=post.source,
        final_score=final_score,
        pain_intensity=d1,
        engagement_norm=d2,
        validation_evidence=d3,
        sentiment_intensity=d4,
        recency=d5,
        trend_momentum=d6,
        market_signal=d7,
        cross_source_bonus=cross_bonus,
        dimensions=dimensions,
        weights=weights,
        computed_at=datetime.now(timezone.utc),
    )


class ScoringModule:
    """Module for computing opportunity scores on posts."""

    def __init__(self, storage: StorageProvider):
        self.storage = storage
        self.storage.initialize()

    def compute_score(
        self,
        post: ScrapedPost,
        pain: PainScore,
        weights: Optional[Dict[str, float]] = None,
    ) -> OpportunityScore:
        """Compute opportunity score for a single post."""
        return compute_opportunity_score(post, pain, self.storage, weights)

    def compute_scores_for_posts(
        self,
        posts_with_pain: List[tuple[ScrapedPost, PainScore]],
        weights: Optional[Dict[str, float]] = None,
    ) -> List[OpportunityScore]:
        """Compute opportunity scores for multiple posts."""
        scores = []
        for post, pain in posts_with_pain:
            try:
                score = self.compute_score(post, pain, weights)
                scores.append(score)
            except Exception as e:
                logger.error(f"Error computing score for post {post.id}: {e}")

        return sorted(scores, key=lambda s: s.final_score, reverse=True)

    def get_top_opportunities(
        self,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> List[OpportunityScore]:
        """Get top opportunity scores from storage."""
        return self.storage.get_opportunity_scores(limit=limit, min_score=min_score)
