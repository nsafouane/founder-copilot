import pytest
from typer.testing import CliRunner
from copilot.cli.main import app
from copilot.models.schemas import ScrapedPost, PainScore, OpportunityScore
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

runner = CliRunner()


@pytest.fixture
def mock_registry():
    with patch("copilot.cli.main.get_registry") as mock:
        registry = MagicMock()
        mock.return_value = registry

        # Mock storage
        storage = MagicMock()
        registry.get_storage.return_value = storage

        # Mock LLM
        llm = MagicMock()
        registry.get_llm.return_value = llm

        # Mock Scraper
        scraper = MagicMock()
        registry.get_scraper.return_value = scraper

        yield registry


def test_discover_with_target_g2(mock_registry):
    """Test discover command with --source and --target flags."""
    with patch("copilot.cli.main.DiscoveryModule") as mock_mod:
        instance = mock_mod.return_value
        instance.discover.return_value = []

        # We need to catch the console.status output which often isn't in stdout in tests
        # or just check that it called discover correctly
        result = runner.invoke(app, ["discover", "--source", "g2", "--target", "slack"])

        assert result.exit_code == 0

        # Verify it was called with targets dict
        mock_mod.return_value.discover.assert_called_once_with(
            {"g2": ["slack"]}, min_score=0.0
        )


def test_rank_command(mock_registry):
    """Test rank command logic."""
    storage = mock_registry.get_storage.return_value
    post = ScrapedPost(
        id="test_id",
        source="reddit",
        title="Test",
        author="user",
        url="url",
        upvotes=1,
        comments_count=1,
        created_at=datetime.now(timezone.utc),
    )
    storage.get_posts.return_value = [post]
    storage.get_post_by_id.return_value = post  # Fix: mock get_post_by_id
    storage.get_signal.return_value = PainScore(score=0.5, reasoning="test")

    with patch("copilot.cli.main.ScoringModule") as mock_scoring:
        scoring_instance = mock_scoring.return_value
        scoring_instance.compute_scores_for_posts.return_value = [
            OpportunityScore(post_id="test_id", source="reddit", final_score=0.8)
        ]

        result = runner.invoke(app, ["rank", "--limit", "1"])

        assert result.exit_code == 0
        # assert "Re-ranking posts" in result.stdout  # Inside status spinner, not captured
        assert "Top 20 Re-Ranked" in result.stdout


def test_sentiment_command(mock_registry):
    """Test sentiment command logic."""
    storage = mock_registry.get_storage.return_value
    post = ScrapedPost(
        id="test_id",
        source="reddit",
        title="Test",
        author="user",
        url="url",
        upvotes=1,
        comments_count=1,
        created_at=datetime.now(timezone.utc),
    )
    storage.get_posts.return_value = [post]
    storage.get_signal.return_value = None  # Force analysis

    with patch("copilot.cli.main.get_discovery_module") as mock_get_discovery:
        discovery_instance = mock_get_discovery.return_value
        discovery_instance.analyze_pain_intensity.return_value = PainScore(
            score=0.5,
            reasoning="test",
            sentiment_label="neutral",
            sentiment_intensity=0.2,
        )

        result = runner.invoke(app, ["sentiment", "--limit", "1"])

        assert result.exit_code == 0
        # assert "Analyzing sentiment" in result.stdout # Inside status spinner
        assert "Successfully analyzed and updated 1 posts" in result.stdout
