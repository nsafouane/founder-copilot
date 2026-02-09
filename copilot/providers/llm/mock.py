from typing import Dict, Any
from ..base import LLMProvider
import json

class MockLLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "mock"

    def configure(self, config: Dict[str, Any]) -> None:
        pass

    def complete(self, prompt: str, **kwargs) -> str:
        prompt_lower = prompt.lower()
        if "persona" in prompt_lower:
            return json.dumps({
                "persona_name": "Test Founder",
                "demographics": {"role": "Founder", "company_size": "1-10", "industry": "SaaS", "experience_level": "Intermediate"},
                "top_pain_points": ["Cost of user acquisition", "Technical debt"],
                "buying_triggers": ["Scalability issues"],
                "channels": ["Reddit", "HN"],
                "messaging_hooks": ["Save 50% on AWS"],
                "willingness_to_pay": "High"
            })
        if "pain point" in prompt_lower:
            return json.dumps({
                "score": 0.85,
                "reasoning": "High signal pain point confirmed by mock LLM",
                "detected_problems": ["Manual data entry"],
                "suggested_solutions": ["Automated CRM integration"],
                "sentiment_label": "frustrated",
                "sentiment_intensity": 0.8,
                "engagement_score": 0.7,
                "validation_score": 0.6,
                "recency_score": 0.9,
                "composite_value": 0.8
            })
        return json.dumps({"result": "success"})
