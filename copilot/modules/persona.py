import logging
import json
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from ..providers.base import LLMProvider
from ..providers.storage.base import StorageProvider
from ..models.schemas import ScrapedPost, PainScore, OpportunityScore

logger = logging.getLogger(__name__)


class Persona(BaseModel):
    """Represents a target customer profile (avatar)."""

    name: str
    role: str  # e.g., "CTO", "Startup Founder", "Product Manager"
    company: str
    industry: str
    pain_points: List[str]
    personality: str  # e.g., "Analytical", "Impulsive Buyer"
    budget_range: str  # e.g., "$50-100/mo", "Enterprise budget"
    preferred_communication: str  # e.g., "Email", "LinkedIn DM"
    buying_triggers: List[str]
    decision_maker: str

    # Alias budget to budget_range for backward compat if needed, or just use budget_range
    @property
    def budget(self) -> str:
        return self.budget_range


class PersonaProfile(BaseModel):
    """Full customer profile including avatar and analysis."""

    persona: Persona
    analysis: str  # AI-generated analysis of why this persona fits the opportunity
    opportunity_fit_score: float  # 0-1, how well their pains match the discovery
    generated_at: str  # ISO 8601 timestamp


class PersonaModule:
    """
    Generates target customer profiles (avatars) based on discovered pain points.

    Uses LLM to create realistic personas with roles, goals, and buying triggers.
    """

    def __init__(self, llm: LLMProvider, storage: Optional[StorageProvider] = None):
        self.llm = llm
        self.storage = storage

        if self.storage:
            self.storage.initialize()

    def _extract_persona_context(self, post: ScrapedPost) -> str:
        """Extract key pain point details from a post for persona generation."""
        pain_details = ""

        if post.body:
            pain_details += f"Body: {post.body[:200]}\n\n"

        # Safe access to dynamic attrs if any
        pain_score = getattr(post, "pain_score", 0)
        if isinstance(pain_score, PainScore):
            score_val = pain_score.score
            probs = pain_score.detected_problems
        else:
            score_val = 0
            probs = []

        return f"""
PAIN POINT ANALYSIS:
Title: {post.title}
Source: {post.source}
Upvotes: {post.upvotes}
Pain Intensity: {score_val}
Detected Problems: {probs}

PROBLEM CONTEXT:
This is a SaaS-related discussion where potential customers are expressing frustration, needs, or desires for better tools.
"""

    def generate_profile(
        self,
        post: ScrapedPost,
        persona_type: str = "startup_founder",  # Default type
    ) -> PersonaProfile:
        """
        Generate a detailed customer persona based on a pain point.

        Args:
            post: The pain point post
            persona_type: Type of persona (e.g., "enterprise_cto", "startup_founder")
        """
        context = self._extract_persona_context(post)

        system_prompt = f"""
You are an expert B2B market researcher and customer avatar creator.
Your task is to generate a detailed, realistic customer persona (avatar) based on the following SaaS pain point analysis.

{context}

Generate a JSON object with this exact schema:
{{
    "persona": {{
        "name": "string - realistic name for this persona",
        "role": "string - job title or function (e.g., CTO, Product Manager, VP of Sales)",
        "company": "string - company name (or 'Self-employed')",
        "industry": "string - industry sector",
        "pain_points": ["list of strings - 3-5 specific pain points this persona faces"],
        "personality": "string - 1-2 words describing their communication style and decision-making traits",
        "budget": "string - budget range or willingness to pay (e.g., '$50-100/mo', 'Open to enterprise pricing', 'Looking for free tools first')",
        "preferred_communication": "string - how they prefer to be contacted (e.g., 'Email', 'LinkedIn InMail', 'Slack', 'Cold call via LinkedIn')",
        "buying_triggers": ["list of strings - what makes them decide to buy a new tool (e.g., 'Current tool slow', 'Missing a feature critical for workflow', 'Boss requested evaluation of alternatives')"],
        "decision_maker": "string - who makes the final decision (Self, Team, CEO approval)",
        "avatar_goals": ["list of strings - what they hope to achieve with a new SaaS tool (e.g., 'Increase team productivity', 'Reduce costs', 'Improve collaboration', 'Automate repetitive tasks')"]
    }},
    "analysis": "string - 2-3 sentences explaining why this persona is a good fit for the opportunity described in the pain point."
}}

Return ONLY valid JSON. Do not include any other text, markdown, or explanations.
"""

        try:
            response_text = self.llm.complete(
                prompt=system_prompt,
                system_prompt="You are a JSON expert. Output ONLY valid JSON.",
            )

            data = json.loads(response_text)

            # Extract persona data
            persona_data = data.get("persona", {})

            # Create Persona object
            persona = Persona(
                name=persona_data.get("name", "Unknown Persona"),
                role=persona_data.get("role", "Unknown"),
                company=persona_data.get("company", "Unknown"),
                industry=persona_data.get("industry", "Unknown"),
                pain_points=persona_data.get("pain_points", []),
                personality=persona_data.get("personality", ""),
                budget_range=persona_data.get(
                    "budget", "Unknown"
                ),  # Map 'budget' from JSON to 'budget_range'
                preferred_communication=persona_data.get(
                    "preferred_communication", "Email"
                ),
                buying_triggers=persona_data.get("buying_triggers", []),
                decision_maker=persona_data.get("decision_maker", "Self"),
            )

            # Generate analysis
            analysis = persona_data.get("analysis", "")
            fit_score = 0.7  # Default moderate fit

            profile = PersonaProfile(
                persona=persona,
                analysis=analysis,
                opportunity_fit_score=fit_score,
                generated_at=datetime.now().isoformat(),
            )

            # Persist to storage if available
            if self.storage:
                # We'd need a save_persona method in StorageProvider, but we'll log it for now
                logger.info(f"Generated persona: {persona.name} ({persona.role})")

            return profile

        except Exception as e:
            logger.error(f"Error generating persona for post {post.id}: {e}")

            # Return a fallback persona
            return PersonaProfile(
                persona=Persona(
                    name="Fallback User",
                    role="Potential Customer",
                    company="Unknown",
                    industry="Software/SaaS",
                    pain_points=[post.title],
                    personality="Cautious explorer",
                    budget_range="Undecided",
                    preferred_communication="Email",
                    buying_triggers=["Researching alternatives"],
                    decision_maker="Self",
                ),
                analysis="Failed to generate detailed persona. Using fallback.",
                opportunity_fit_score=0.5,
                generated_at=datetime.now().isoformat(),
            )

    def generate_profiles_for_opportunities(
        self,
        scored_posts: List[OpportunityScore],
        persona_type: str = "startup_founder",
        limit: int = 5,
    ) -> List[PersonaProfile]:
        """
        Generate personas for the top N opportunity scores.

        Args:
            scored_posts: List of OpportunityScore objects
            persona_type: Type of persona to generate
            limit: Number of profiles to generate
        """
        profiles = []

        for score in scored_posts[:limit]:
            if not self.storage:
                logger.warning(
                    "Storage not available to fetch post details for persona generation."
                )
                continue

            post = self.storage.get_post_by_id(score.post_id)
            if not post:
                continue

            profile = self.generate_profile(post, persona_type=persona_type)
            profiles.append(profile)

        logger.info(
            f"Generated {len(profiles)} personas for top {limit} opportunities."
        )
        return profiles
