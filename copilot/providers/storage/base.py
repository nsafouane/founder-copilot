from abc import ABC, abstractmethod
from typing import List, Optional
from ...models.schemas import (
    ScrapedPost,
    PainScore,
    Lead,
    ValidationReport,
    OpportunityScore,
)


class StorageProvider(ABC):
    """Canonical storage interface. All storage backends MUST implement this."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass

    # --- Posts ---
    @abstractmethod
    def save_post(self, post: ScrapedPost) -> None:
        pass

    @abstractmethod
    def get_posts(
        self, limit: int = 100, source: Optional[str] = None
    ) -> List[ScrapedPost]:
        pass

    @abstractmethod
    def get_post_by_id(self, post_id: str) -> Optional[ScrapedPost]:
        pass

    # --- Signals / Analysis ---
    @abstractmethod
    def save_signal(self, post_id: str, pain_info: PainScore) -> None:
        pass

    @abstractmethod
    def get_signal(self, post_id: str) -> Optional[PainScore]:
        pass

    # --- Opportunity Scores ---
    @abstractmethod
    def save_opportunity_score(self, score: OpportunityScore) -> None:
        pass

    @abstractmethod
    def get_opportunity_scores(
        self, limit: int = 100, min_score: float = 0.0
    ) -> List[OpportunityScore]:
        pass

    # --- Leads ---
    @abstractmethod
    def save_lead(self, lead: Lead) -> None:
        pass

    @abstractmethod
    def get_leads(self, limit: Optional[int] = 100) -> List[Lead]:
        pass

    # --- Reports ---
    @abstractmethod
    def save_report(self, report: ValidationReport) -> None:
        pass

    @abstractmethod
    def get_reports(self, limit: Optional[int] = None) -> List[ValidationReport]:
        pass
