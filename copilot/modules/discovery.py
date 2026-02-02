import json
import logging
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

    def discover(self, subreddits: List[str], min_score: float = 0.7) -> List[tuple[ScrapedPost, PainScore]]:
        """Run full discovery pipeline: scrape -> analyze -> filter."""
        posts = self.fetch_potential_pains(subreddits)
        results = []
        
        for post in posts:
            # Basic heuristic filtering before LLM to save tokens/time
            if post.upvotes < 5 and post.comments_count < 2:
                continue
                
            pain_score = self.analyze_pain_intensity(post)
            if pain_score.score >= min_score:
                results.append((post, pain_score))
                
        # Sort by score descending
        results.sort(key=lambda x: x[1].score, reverse=True)
        return results
