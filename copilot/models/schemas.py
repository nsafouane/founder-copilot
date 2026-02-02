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
    subreddit: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PainScore(BaseModel):
    """Model for pain point intensity scoring."""
    score: float = Field(..., ge=0, le=1)
    reasoning: str
    detected_problems: List[str] = Field(default_factory=list)
    suggested_solutions: List[str] = Field(default_factory=list)
    
    # New metrics for composite scoring
    engagement_score: float = Field(default=0.0, ge=0, le=1)
    validation_score: float = Field(default=0.0, ge=0, le=1)
    recency_score: float = Field(default=0.0, ge=0, le=1)
    composite_value: float = Field(default=0.0, ge=0, le=1)
