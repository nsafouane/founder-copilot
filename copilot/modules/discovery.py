import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from ..providers.base import ScraperProvider, LLMProvider
from ..models.schemas import ScrapedPost, PainScore

logger = logging.getLogger(__name__)

class DiscoveryModule:
    """Core logic for finding and classifying high-signal pain points."""
    
    def __init__(self, scraper: ScraperProvider, llm: LLMProvider):
        self.scraper = scraper
        self.llm = llm
        
    def fetch_potential_pains(self, target_subreddits: List[str], limit_per_sub: int = 50) -> List[ScrapedPost]:
        """Fetch posts from target subreddits."""
        all_posts = []
        for sub in target_subreddits:
            try:
                posts = self.scraper.scrape(source="reddit", target=sub, limit=limit_per_sub)
                all_posts.extend(posts)
            except Exception as e:
                logger.error(f"Error scraping r/{sub}: {e}")
        return all_posts

    def analyze_pain_intensity(self, post: ScrapedPost) -> PainScore:
        """Use LLM to analyze the intensity of the pain point described in a post."""
        
        prompt = f"""
        Analyze the following social media post to determine if it expresses a 'pain point' (a problem, frustration, or unmet need).
        
        Title: {post.title}
        Body: {post.body or 'N/A'}
        
        Return a JSON object with:
        - score: A float between 0.0 and 1.0 (0 = no pain, 1 = high intensity/frequent problem)
        - reasoning: A brief explanation of why you gave this score.
        - detected_problems: A list of specific problems mentioned.
        - suggested_solutions: A list of potential solutions or app ideas that could solve this.
        - validation_score: A float between 0.0 and 1.0 (How much validation/evidence of need is in the post?)
        """
        
        system_prompt = "You are an expert product researcher specializing in identifying high-signal founder opportunities from social signals. You output strictly valid JSON."
        
        try:
            response_text = self.llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response_text)
            return PainScore(**data)
        except Exception as e:
            logger.error(f"Error analyzing post {post.id}: {e}")
            return PainScore(score=0.0, reasoning=f"Analysis failed: {str(e)}")

    def calculate_engagement_score(self, post: ScrapedPost) -> float:
        """Calculate engagement score (0-1) based on upvotes and comments."""
        # Heuristic: 100 upvotes + 50 comments = 1.0
        score = (post.upvotes * 0.5 + post.comments_count * 1.0) / 100.0
        return min(1.0, score)

    def calculate_recency_score(self, post: ScrapedPost) -> float:
        """Calculate recency score (0-1)."""
        now = datetime.now(timezone.utc)
        
        # Ensure post.created_at is timezone aware
        created_at = post.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
            
        delta = now - created_at
        days = delta.days
        
        if days < 1: return 1.0
        if days < 7: return 0.8
        if days < 30: return 0.5
        if days < 90: return 0.2
        return 0.0

    def discover(self, subreddits: List[str], min_score: float = 0.5) -> List[tuple[ScrapedPost, PainScore]]:
        """Run full discovery pipeline: scrape -> analyze -> filter."""
        posts = self.fetch_potential_pains(subreddits)
        results = []
        
        for post in posts:
            # Basic heuristic filtering before LLM to save tokens/time
            if post.upvotes < 5 and post.comments_count < 2:
                continue
                
            pain_info = self.analyze_pain_intensity(post)
            
            # Calculate composite metrics
            pain_info.engagement_score = self.calculate_engagement_score(post)
            pain_info.recency_score = self.calculate_recency_score(post)
            
            # Formula: Value = (Pain * 0.4) + (Engagement * 0.25) + (Validation * 0.25) + (Recency * 0.10)
            pain_info.composite_value = (
                (pain_info.score * 0.4) +
                (pain_info.engagement_score * 0.25) +
                (pain_info.validation_score * 0.25) +
                (pain_info.recency_score * 0.10)
            )
            
            if pain_info.composite_value >= min_score:
                results.append((post, pain_info))
                
        # Sort by composite value descending
        results.sort(key=lambda x: x[1].composite_value, reverse=True)
        return results
