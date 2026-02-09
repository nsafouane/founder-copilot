import logging
import json
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from ..providers.base import ScraperProvider, LLMProvider
from ..providers.storage.base import StorageProvider
from ..models.schemas import ScrapedPost, PainScore, ValidationReport
from ..core.config import ConfigManager
import os

if TYPE_CHECKING:
    from .discovery import DiscoveryModule

logger = logging.getLogger(__name__)


class MonitorModule:
    """Automated monitoring of subreddits for specific competitor mentions or keywords."""

    def __init__(
        self,
        discovery: "DiscoveryModule",
        llm: LLMProvider,
        storage: Optional[StorageProvider] = None,
    ):
        self.discovery = discovery
        self.llm = llm
        self.storage = storage
        self.config = ConfigManager()
        self.tavily_api_key = self.config.get("tavily_api_key")

    def _trigger_deep_research_cycle(
        self,
        post_id: str,
        competitor_name: str,
        post: ScrapedPost,
        pain_info: PainScore,
    ) -> Optional[ValidationReport]:
        """
        Triggers a deep research cycle using the deep-research skill (via Gemini CLI + Tavily MCP)
        to generate a "Real Landscape Analysis" report.
        """
        if not self.tavily_api_key:
            logger.warning(
                "TAVILY_API_KEY not configured. Deep research will not be performed."
            )
            return None

        # Craft a comprehensive prompt for the Gemini deep-research skill
        gemini_prompt = f"""
        Conduct a "Real Landscape Analysis" for the competitor '{competitor_name}' in relation to the market need identified in the following Reddit post.
        
        **Reddit Post Details:**
        - Title: {post.title}
        - Body: {post.body or "N/A"}
        - URL: {post.url}
        - Subreddit: r/{post.subreddit}
        
        **Identified Pain Point:**
        - Score: {pain_info.score:.2f}
        - Reasoning: {pain_info.reasoning}
        - Detected Problems: {", ".join(pain_info.detected_problems)}
        - Suggested Solutions (from Reddit): {", ".join(pain_info.suggested_solutions)}
        
        Using the 'tavily-mcp' tool, search for information about '{competitor_name}', focusing on their:
        - Product offerings and features
        - Business model and pricing
        - Target audience
        - Funding rounds and investors
        - Recent news and developments (last 12-18 months)
        - Strengths, Weaknesses, Opportunities, and Threats in relation to the identified Reddit pain point.

        Synthesize all findings, including the Reddit post context, into a JSON object that strictly adheres to the 'ValidationReport' schema.
        
        **ValidationReport Schema (JSON format):**
        {{
            "post_id": "string",
            "idea_summary": "string - summarize the core idea/problem from Reddit",
            "market_size_estimate": "string - based on the research, estimate market size/opportunity related to the problem",
            "competitors": [
                {{"Name": "string", "URL": "string", "Description": "string"}}
            ],
            "swot_analysis": {{
                "Strengths": ["string"],
                "Weaknesses": ["string"],
                "Opportunities": ["string"],
                "Threats": ["string"]
            }},
            "validation_verdict": "string - overall assessment of the competitor's landscape and market opportunity",
            "next_steps": ["string"],
            "generated_at": "datetime string (ISO 8601 format)"
        }}
        
        Ensure the JSON output is complete and valid.
        """

        try:
            # Using the exec tool to run the gemini CLI command
            # The output should be raw JSON from Gemini
            gemini_command = [
                "gemini",
                "-m",
                "gemini-2.5-flash",  # Specify model if needed, or rely on default
                "-p",
                gemini_prompt,
            ]

            logger.info(
                f"Triggering deep research for {competitor_name} with Gemini..."
            )
            result = exec(command=gemini_command)

            if result.exit_code != 0:
                logger.error(f"Gemini CLI command failed: {result.stderr}")
                return None

            # Attempt to parse the output as JSON
            report_data = json.loads(result.stdout)

            # Ensure generated_at is correctly set if not provided by LLM or is string
            if "generated_at" in report_data and isinstance(
                report_data["generated_at"], str
            ):
                try:
                    report_data["generated_at"] = datetime.fromisoformat(
                        report_data["generated_at"]
                    )
                except ValueError:
                    report_data["generated_at"] = datetime.now()
            elif "generated_at" not in report_data:
                report_data["generated_at"] = datetime.now()

            report_data["post_id"] = (
                post_id  # Ensure the report is linked to the original post
            )

            return ValidationReport(**report_data)

        except Exception as e:
            logger.error(f"Error during deep research for {competitor_name}: {e}")
            return None

    def monitor_competitors(self, subreddits: List[str], competitors: List[str]) -> int:
        """
        Scan subreddits for new mentions of competitors.
        Updates the database with any new high-signal posts and triggers deep research.
        Returns the number of new signals found.
        """
        count = 0
        deep_research_reports_generated = 0

        for sub in subreddits:
            try:
                posts = self.discovery.scraper.scrape(
                    source="reddit", target=sub, limit=50
                )
                for post in posts:
                    content = f"{post.title} {post.body or ''}".lower()

                    for comp in competitors:
                        if comp.lower() in content:
                            logger.info(
                                f"Monitor found mention of competitor '{comp}' in r/{sub}: {post.title}"
                            )

                            # Analyze and save post/signal first
                            pain_info = self.discovery.analyze_pain_intensity(post)
                            if self.storage:
                                self.storage.save_post(post)
                                self.storage.save_signal(post.id, pain_info)
                            count += 1

                            # Trigger deep research cycle
                            report = self._trigger_deep_research_cycle(
                                post.id, comp, post, pain_info
                            )
                            if report and self.storage:
                                self.storage.save_report(report)
                                deep_research_reports_generated += 1
                                logger.info(
                                    f"Generated deep research report for '{comp}' related to post {post.id}"
                                )

            except Exception as e:
                logger.error(f"Error monitoring r/{sub}: {e}")

        logger.info(
            f"Monitoring complete. Found {count} competitor mentions and generated {deep_research_reports_generated} deep research reports."
        )
        return count  # Or return deep_research_reports_generated if that's the primary metric for this function

    def run_periodic_discovery(
        self, subreddits: List[str], min_score: float = 0.5
    ) -> int:
        """Run discovery on a schedule (manual trigger for now) and save results."""
        results = self.discovery.discover(subreddits, min_score=min_score)
        return len(results)
