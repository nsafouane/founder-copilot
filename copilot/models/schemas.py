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
