import logging
from typing import List, Optional
from datetime import datetime
from ..providers.base import ScraperProvider
from ..providers.storage.base import StorageProvider
from .discovery import DiscoveryModule

logger = logging.getLogger(__name__)

class MonitorModule:
    """Automated monitoring of subreddits for specific competitor mentions or keywords."""

    def __init__(self, discovery: DiscoveryModule, storage: Optional[StorageProvider] = None):
        self.discovery = discovery
        self.storage = storage

    def monitor_competitors(self, subreddits: List[str], competitors: List[str]) -> int:
        """
        Scan subreddits for new mentions of competitors.
        Updates the database with any new high-signal posts.
        Returns the number of new signals found.
        """
        count = 0
        # For each subreddit, we use the discovery module's scraping logic
        # but filter specifically for competitor mentions in title or body.
        
        for sub in subreddits:
            try:
                posts = self.discovery.scraper.scrape(source="reddit", target=sub, limit=50)
                for post in posts:
                    content = f"{post.title} {post.body or ''}".lower()
                    if any(comp.lower() in content for comp in competitors):
                        # Analyze and save if it's a mention
                        pain_info = self.discovery.analyze_pain_intensity(post)
                        
                        if self.storage:
                            self.storage.save_post(post)
                            self.storage.save_signal(post.id, pain_info)
                        
                        count += 1
                        logger.info(f"Monitor found mention of competitor in r/{sub}: {post.title}")
                        
            except Exception as e:
                logger.error(f"Error monitoring r/{sub}: {e}")
                
        return count

    def run_periodic_discovery(self, subreddits: List[str], min_score: float = 0.5) -> int:
        """Run discovery on a schedule (manual trigger for now) and save results."""
        results = self.discovery.discover(subreddits, min_score=min_score)
        return len(results)
