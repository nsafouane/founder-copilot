import logging
import json
from typing import List, Optional
from ..providers.base import LLMProvider
from ..providers.storage.base import StorageProvider
from ..models.schemas import Lead, ScrapedPost

logger = logging.getLogger(__name__)

class LeadModule:
    """Identify potential customers (leads) from social posts based on intent."""

    INTENT_KEYWORDS = ["recommend", "looking for", "how do I", "alternative to", "best tool for"]

    def __init__(self, llm: LLMProvider, storage: Optional[StorageProvider] = None):
        self.llm = llm
        self.storage = storage

    def scan_for_leads(self, post_limit: int = 100) -> List[Lead]:
        """Scan stored posts for high-intent leads."""
        if not self.storage:
            return []

        posts = self.storage.get_posts(limit=post_limit)
        leads = []

        for post in posts:
            content = f"{post.title} {post.body or ''}".lower()
            if any(kw in content for kw in self.INTENT_KEYWORDS):
                lead = self.extract_lead_intent(post)
                if lead and lead.intent_score >= 0.6:
                    leads.append(lead)
                    # Note: We need a storage method for leads
                    self._save_lead(lead)
        
        return leads

    def extract_lead_intent(self, post: ScrapedPost) -> Optional[Lead]:
        """Use LLM to score intent and extract details."""
        prompt = f"""
        Analyze the following post for 'purchase intent' or 'problem-solving intent'.
        The user is looking for a solution, recommendation, or alternative.
        
        Post: {post.title}
        Content: {post.body or 'N/A'}
        
        Return a JSON object:
        {{
            "intent_score": float (0-1),
            "content_snippet": "short summary of what they need",
            "reasoning": "why this is a lead"
        }}
        """
        
        try:
            response = self.llm.complete(
                prompt=prompt,
                system_prompt="You are a lead generation specialist. Identify users who are actively looking for solutions.",
                response_format={"type": "json_object"}
            )
            data = json.loads(response)
            
            return Lead(
                post_id=post.id,
                author=post.author,
                content_snippet=data.get("content_snippet", post.title[:100]),
                intent_score=data.get("intent_score", 0.0),
                contact_url=post.url,
                status="new"
            )
        except Exception as e:
            logger.error(f"Error extracting lead from {post.id}: {e}")
            return None

    def _save_lead(self, lead: Lead):
        """Internal helper to save lead to SQLite."""
        # This requires adding a save_lead method to the StorageProvider interface and SQLite implementation
        if hasattr(self.storage, 'save_lead'):
            self.storage.save_lead(lead)
