import pytest
from unittest.mock import MagicMock, patch
from copilot.modules.validation import ValidationModule
from copilot.models.schemas import ScrapedPost, ValidationReport
from datetime import datetime

@pytest.fixture
def mock_storage():
    return MagicMock()

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.fixture
def validation_module(mock_llm, mock_storage):
    return ValidationModule(llm=mock_llm, storage=mock_storage)

def test_deep_research_landscape_mapping(validation_module, mock_storage):
    # Setup mock post
    post = ScrapedPost(
        id="post_deep_1",
        source="reddit",
        title="I need a tool for automated invoice parsing",
        body="Manually entering invoices is killing my productivity.",
        author="busy_founder",
        url="http://reddit.com/post1",
        upvotes=10,
        comments_count=5,
        created_at=datetime.now()
    )
    mock_storage.get_post_by_id.return_value = post
    
    # Mock subprocess.run for gemini CLI deep research
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """
        {
            "idea_summary": "Automated invoice parsing tool for founders.",
            "market_size_estimate": "Estimated $5B market by 2027.",
            "competitors": [
                {"name": "Rossum", "url": "https://rossum.ai", "description": "AI invoice extraction"},
                {"name": "Bill.com", "url": "https://bill.com", "description": "Accounts payable automation"}
            ],
            "swot_analysis": {
                "strengths": ["Speed", "Accuracy"],
                "weaknesses": ["Price"],
                "opportunities": ["SMB focus"],
                "threats": ["Established players"]
            },
            "validation_verdict": "GO",
            "next_steps": ["Build MVP with Tesseract"]
        }
        """
        
        report = validation_module.validate_idea("post_deep_1", deep=True)
        
        assert report.post_id == "post_deep_1"
        assert report.validation_verdict == "GO"
        assert len(report.competitors) == 2
        assert report.competitors[0]["name"] == "Rossum"
        mock_storage.save_report.assert_called_with(report)

def test_deep_research_landscape_fail(validation_module, mock_storage):
    post = ScrapedPost(
        id="post_fail",
        source="reddit",
        title="Test",
        author="user",
        url="url",
        upvotes=1,
        comments_count=1,
        created_at=datetime.now()
    )
    mock_storage.get_post_by_id.return_value = post
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "CLI Error"
        
        with pytest.raises(RuntimeError, match="Deep research failed"):
            validation_module.validate_idea("post_fail", deep=True)
