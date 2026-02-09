import logging
import json
import time
from typing import List, Optional, Dict
from ..providers.base import LLMProvider
from ..providers.storage.base import StorageProvider
from ..models.schemas import Lead, ScrapedPost
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


class LeadModule:
    """Identify potential customers (leads) from social posts based on intent."""

    INTENT_KEYWORDS = [
        "recommend",
        "looking for",
        "how do I",
        "alternative to",
        "best tool for",
    ]

    def __init__(self, llm: LLMProvider, storage: Optional[StorageProvider] = None):
        self.llm = llm
        self.storage = storage
        self.config = ConfigManager()
        self.llm_request_delay = float(self.config.get("llm_request_delay", 2))

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
        Content: {post.body or "N/A"}
        
        Return a JSON object:
        {{
            "intent_score": float (0-1),
            "content_snippet": "short summary of what they need",
            "reasoning": "why this is a lead"
        }}
        """

        try:
            time.sleep(self.llm_request_delay)  # Added delay before LLM call
            response = self.llm.complete(
                prompt=prompt,
                system_prompt="You are a lead generation specialist. Identify users who are actively looking for solutions.",
                response_format={"type": "json_object"},
            )
            data = json.loads(response)

            return Lead(
                post_id=post.id,
                author=data.get(
                    "author", post.author
                ),  # Adjusted to use author from LLM if available, else post.author
                content_snippet=data.get("content_snippet", post.title[:100]),
                intent_score=data.get("intent_score", 0.0),
                contact_url=post.url,
                status="new",
            )
        except Exception as e:
            logger.error(f"Error extracting lead from {post.id}: {e}")
            return None

    def _save_lead(self, lead: Lead):
        """Internal helper to save lead to SQLite."""
        # This requires adding a save_lead method to the StorageProvider interface and SQLite implementation
        if hasattr(self.storage, "save_lead"):
            self.storage.save_lead(lead)

    def verify_leads_multi_channel(self, limit: int = 10) -> int:
        """
        Scan for 'new' leads and attempt to verify them on LinkedIn and Twitter
        using deep research (Gemini CLI + Tavily MCP).
        """
        if not self.storage:
            return 0

        leads = self.storage.get_leads(limit=limit)
        new_leads = [l for l in leads if l.status == "new"]
        verified_count = 0

        for lead in new_leads:
            logger.info(f"Verifying lead: {lead.author} from {lead.source}")
            verified_profiles = self._research_social_profiles(lead.author, lead.source)

            if verified_profiles:
                lead.verified_profiles.update(verified_profiles)
                lead.status = "verified"
                # Update in storage (Requires update_lead or re-save)
                # For now, re-save if save_lead handles REPLACE or if we add update_lead
                if hasattr(self.storage, "save_lead"):
                    # Note: save_lead currently uses INSERT, not REPLACE in SQLiteProvider
                    # We might need to update SQLiteProvider.save_lead
                    self.storage.save_lead(lead)
                verified_count += 1

        return verified_count

    def _research_social_profiles(self, username: str, platform: str) -> Dict[str, str]:
        """
        Uses Gemini CLI + Tavily MCP to find LinkedIn and Twitter profiles.
        """
        prompt = f"""
        Research the social media presence of the user '{username}' who is active on {platform}.
        Try to find their LinkedIn and Twitter/X profiles.
        
        Return a JSON object:
        {{
            "linkedin": "url or null",
            "twitter": "url or null"
        }}
        """

        try:
            from ..core.config import ConfigManager
            import subprocess

            # Using subprocess to call 'gemini' CLI
            cmd = ["gemini", "-m", "gemini-2.5-flash", "-p", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Gemini CLI error during verification: {result.stderr}")
                return {}

            # Attempt to parse JSON from stdout
            output = result.stdout.strip()
            # Clean markdown if present
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()

            data = json.loads(output)
            # Filter out nulls
            return {k: v for k, v in data.items() if v}

        except Exception as e:
            logger.error(f"Error researching social profiles for {username}: {e}")
            return {}
