import json
import logging
from typing import List, Optional
from ..providers.base import LLMProvider
from ..providers.storage.base import StorageProvider
from ..models.schemas import ValidationReport, ScrapedPost

logger = logging.getLogger(__name__)

class ValidationModule:
    """Deep validation and research for specific pain points."""

    def __init__(self, llm: LLMProvider, storage: Optional[StorageProvider] = None):
        self.llm = llm
        self.storage = storage

    def validate_idea(self, post_id: str, deep: bool = False) -> ValidationReport:
        """Perform research on a post's pain point and generate a report."""
        
        # 1. Fetch post from storage
        post = None
        if self.storage:
            post = self.storage.get_post_by_id(post_id)
        
        if not post:
            raise ValueError(f"Post {post_id} not found in storage. Run discovery first.")

        if deep:
            return self.deep_research_landscape(post)

        # 2. Standard Research & Report Generation
        prompt = f"""
        Research and validate the potential for a product based on this pain point:
        
        Title: {post.title}
        Context: {post.body or 'N/A'}
        Source: {post.url}
        
        Tasks:
        1. Summarize the core problem and the proposed idea to solve it.
        2. Identify at least 3 existing competitors (real companies or tools).
        3. Provide a SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) for a new entrant.
        4. Estimate market viability (is this a niche, a growing trend, or a saturated market?).
        5. Give a final 'Validation Verdict' (Go/No-Go/Pivot).
        6. List clear next steps for an MVP.
        
        Return a JSON object matching this schema exactly. Ensure all fields in 'swot_analysis' are flat lists of strings:
        {{
            "idea_summary": "string",
            "market_size_estimate": "string",
            "competitors": [
                {{"name": "name", "url": "url", "description": "desc"}}
            ],
            "swot_analysis": {{
                "strengths": ["string"],
                "weaknesses": ["string"],
                "opportunities": ["string"],
                "threats": ["string"]
            }},
            "validation_verdict": "string",
            "next_steps": ["string"]
        }}
        """

        system_prompt = "You are a senior venture researcher and product strategist. You provide data-driven validation reports. Output strictly valid JSON."

        try:
            response_text = self.llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response_text)
            report = ValidationReport(post_id=post_id, source=post.source, **data)
            
            if self.storage:
                self.storage.save_report(report)
            
            return report
        except Exception as e:
            logger.error(f"Error validating idea for post {post_id}: {e}")
            raise

    def deep_research_landscape(self, post: ScrapedPost) -> ValidationReport:
        """
        Uses Gemini CLI + Tavily MCP to perform deep research on the competitive landscape.
        """
        logger.info(f"Triggering deep research landscape mapping for post: {post.id}")
        
        prompt = f"""
        Conduct a comprehensive competitive landscape mapping for the market opportunity identified in this post:
        
        Post Title: {post.title}
        Post Content: {post.body or "N/A"}
        
        Step 1: Use tavily-mcp to search for existing solutions, startups, and established companies addressing this specific pain point.
        Step 2: Identify at least 5-7 competitors with their names, URLs, and key value propositions.
        Step 3: Analyze the market size and current trends using web data.
        Step 4: Synthesize a deep SWOT analysis for a new entrant.
        Step 5: Provide a detailed validation verdict and specific MVP roadmap.
        
        Return a JSON object matching this schema exactly:
        {{
            "idea_summary": "string",
            "market_size_estimate": "string",
            "competitors": [
                {{"name": "name", "url": "url", "description": "desc"}}
            ],
            "swot_analysis": {{
                "strengths": ["string"],
                "weaknesses": ["string"],
                "opportunities": ["string"],
                "threats": ["string"]
            }},
            "validation_verdict": "string",
            "next_steps": ["string"]
        }}
        """

        try:
            import subprocess
            cmd = ["gemini", "-m", "gemini-2.5-flash", "-p", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Deep research CLI error: {result.stderr}")
                raise RuntimeError(f"Deep research failed: {result.stderr}")

            output = result.stdout.strip()
            # Clean markdown if present
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()

            data = json.loads(output)
            report = ValidationReport(post_id=post.id, source=post.source, **data)
            
            if self.storage:
                self.storage.save_report(report)
            
            return report

        except Exception as e:
            logger.error(f"Error during deep research landscape mapping: {e}")
            raise

    def format_report_markdown(self, report: ValidationReport) -> str:
        """Convert a ValidationReport object into a clean markdown string."""
        md = f"# Validation Report for Post {report.post_id}\n\n"
        md += f"## Idea Summary\n{report.idea_summary}\n\n"
        md += f"## Market Context\n{report.market_size_estimate}\n\n"
        
        md += "## Competitors\n"
        for comp in report.competitors:
            md += f"- **{comp.get('name')}**: {comp.get('description')} ([Link]({comp.get('url')}))\n"
        
        md += "\n## SWOT Analysis\n"
        for key, items in report.swot_analysis.items():
            md += f"### {key.capitalize()}\n"
            for item in items:
                md += f"- {item}\n"
        
        md += f"\n## Verdict\n**{report.validation_verdict}**\n\n"
        
        md += "## Next Steps\n"
        for step in report.next_steps:
            md += f"1. {step}\n"
            
        return md
