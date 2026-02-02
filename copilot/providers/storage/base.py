from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ...models.schemas import ScrapedPost, PainScore, Lead

class StorageProvider(ABC):
    """Abstract base class for all storage implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'sqlite')."""
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize database schema."""
        pass
    
    @abstractmethod
    def save_post(self, post: ScrapedPost) -> None:
        """Save a single scraped post."""
        pass

    @abstractmethod
    def save_signal(self, post_id: str, pain_info: PainScore) -> None:
        """Save analysis results (signals) for a post."""
        pass

    @abstractmethod
    def get_posts(self, limit: int = 100) -> List[ScrapedPost]:
        """Retrieve recent posts."""
        pass

    @abstractmethod
    def save_lead(self, lead: Lead) -> None:
        """Save a potential customer lead."""
        pass

    @abstractmethod
    def get_leads(self, limit: int = 100) -> List[Lead]:
        """Retrieve recent leads."""
        pass
