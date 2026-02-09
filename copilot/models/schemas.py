from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ScrapedPost(BaseModel):
    """Unified representation of a post scraped from any source."""

    id: str
    source: str  # e.g., 'reddit', 'hackernews'
    title: str
    body: Optional[str] = None
    author: str
    url: str
    upvotes: int
    comments_count: int
    created_at: datetime

    # REVISED: Generic channel field replaces subreddit
    channel: Optional[str] = None  # NEW: Generic — 'r/saas', 'hn/ask', 'g2/slack', etc.
    subreddit: Optional[str] = (
        None  # KEPT for backward compat (alias for Reddit channels)
    )

    # NEW: Sentiment fields (populated by v1.1 analysis)
    sentiment_label: Optional[str] = (
        None  # 'frustrated', 'desperate', 'curious', 'neutral', 'positive'
    )
    sentiment_intensity: float = 0.0  # 0.0-1.0

    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def display_channel(self) -> str:
        """Human-readable channel for display."""
        if self.channel:
            return self.channel
        if self.subreddit:
            return f"r/{self.subreddit}"
        return self.source


class PainScore(BaseModel):
    """Model for pain point intensity scoring."""

    score: float = Field(..., ge=0, le=1)
    reasoning: str
    detected_problems: List[str] = Field(default_factory=list)
    suggested_solutions: List[str] = Field(default_factory=list)

    # Existing metrics (kept for backward compat)
    engagement_score: float = Field(default=0.0, ge=0, le=1)
    validation_score: float = Field(default=0.0, ge=0, le=1)
    recency_score: float = Field(default=0.0, ge=0, le=1)
    composite_value: float = Field(default=0.0, ge=0, le=1)  # v1.0 formula

    # NEW: Sentiment fields
    sentiment_label: Optional[str] = None
    sentiment_intensity: float = Field(default=0.0, ge=0, le=1)


class OpportunityScore(BaseModel):
    """Unified cross-platform opportunity ranking score."""

    post_id: str
    source: str  # Post's source platform
    final_score: float = Field(..., ge=0, le=1)  # The unified score

    # Individual dimensions (all 0-1)
    pain_intensity: float = 0.0
    engagement_norm: float = 0.0
    validation_evidence: float = 0.0
    sentiment_intensity: float = 0.0
    recency: float = 0.0
    trend_momentum: float = 0.0
    market_signal: float = 0.0
    cross_source_bonus: float = 0.0

    # Audit trail
    dimensions: Dict[str, float] = Field(default_factory=dict)  # All dimension values
    weights: Dict[str, float] = Field(default_factory=dict)  # Weights used

    computed_at: datetime = Field(default_factory=datetime.now)


class ValidationReport(BaseModel):
    """Deep research report — now includes multi-source evidence."""

    post_id: str
    source: str = "reddit"  # NEW
    idea_summary: str
    market_size_estimate: str
    competitors: List[Dict[str, str]] = Field(
        default_factory=list
    )  # Name, URL, Description
    swot_analysis: Dict[str, List[str]] = Field(default_factory=dict)
    validation_verdict: str
    next_steps: List[str] = Field(default_factory=list)

    # NEW: Cross-source evidence
    corroborating_sources: List[str] = Field(
        default_factory=list
    )  # Other platforms confirming this pain
    corroborating_post_ids: List[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.now)


class Lead(BaseModel):
    """Potential customer identified from intent — now multi-source."""

    id: Optional[int] = None
    post_id: str
    source: str = "reddit"  # NEW: Which platform the lead came from
    author: str
    content_snippet: str
    intent_score: float = Field(..., ge=0, le=1)
    sentiment_label: Optional[str] = None  # NEW
    sentiment_intensity: float = 0.0  # NEW
    contact_url: str
    verified_profiles: Dict[str, str] = Field(
        default_factory=dict
    )  # NEW: platform -> url (e.g., 'linkedin' -> '...')
    status: str = "new"  # new, contacted, ignore
    created_at: datetime = Field(default_factory=datetime.now)
