from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncIterator
from ..models.schemas import ScrapedPost

class ScraperProvider(ABC):
    """Abstract base class for all scraper implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the provider with credentials and settings."""
        pass
    
    @abstractmethod
    def scrape(
        self,
        source: str,
        target: str,
        limit: int = 100,
        **kwargs
    ) -> List[ScrapedPost]:
        """Scrape posts from a source."""
        pass

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
    def complete(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        pass

class StorageProvider(ABC):
    """Abstract base class for all storage implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        pass
    
    @abstractmethod
    def store_posts(self, posts: List[ScrapedPost]) -> int:
        pass
