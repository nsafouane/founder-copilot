from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from ..models.schemas import ScrapedPost, PainScore


class ScraperCapability(Enum):
    """Declares what a scraper can do."""

    SEARCH = "search"
    SORT_NEW = "sort_new"
    SORT_HOT = "sort_hot"
    SORT_TOP = "sort_top"
    COMMENTS = "comments"
    REVIEWS = "reviews"
    REALTIME = "realtime"
    HISTORICAL = "historical"


class ScraperProvider(ABC):
    """Abstract base class for all scraper implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g., 'reddit', 'hackernews', 'g2')."""
        pass

    @property
    @abstractmethod
    def platform(self) -> str:
        """Human-readable platform name (e.g., 'Reddit', 'Hacker News')."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> Set[ScraperCapability]:
        """Declare supported capabilities for this scraper."""
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure with credentials and settings."""
        pass

    @abstractmethod
    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        """
        Scrape posts/reviews from this provider's platform.

        Args:
            target: Platform-specific target (subreddit name, search query, product slug, etc.)
            limit: Maximum items to return
            **kwargs: Provider-specific options (sort, time_range, etc.)

        Returns:
            List of ScrapedPost with source=self.name
        """
        pass

    def health_check(self) -> bool:
        """Optional: verify API connectivity. Default returns True."""
        return True


class LLMProvider(ABC):
    """Abstract base class for all LLM implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        pass


class CRMProvider(ABC):
    """Abstract base class for all CRM implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g., 'hubspot', 'salesforce')."""
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure with credentials and settings."""
        pass

    @abstractmethod
    def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact in the CRM."""
        pass

    @abstractmethod
    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing contact in the CRM."""
        pass
    
    @abstractmethod
    def create_deal(self, deal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new deal/opportunity in the CRM."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verify API connectivity. Default returns True."""
        return True

