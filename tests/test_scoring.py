import pytest
from datetime import datetime, timezone, timedelta
from copilot.modules.scoring import (
    calculate_engagement_norm,
    calculate_recency_score,
    calculate_market_signal,
    extract_key_terms,
    calculate_trend_momentum,
    calculate_cross_source_bonus,
    compute_opportunity_score,
    ScoringModule,
    WEIGHTS,
)
from copilot.models.schemas import ScrapedPost, PainScore
from copilot.providers.storage.sqlite_provider import SQLiteProvider
import tempfile
import os


@pytest.fixture
def temp_db_path():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def storage(temp_db_path):
    """Create storage provider for testing."""
    storage = SQLiteProvider(db_path=temp_db_path)
    storage.initialize()
    return storage


@pytest.fixture
def reddit_post():
    """Create a sample Reddit post."""
    return ScrapedPost(
        id="test_reddit_1",
        source="reddit",
        title="Frustrated with slow SaaS tools",
        body="I'm looking for alternatives to Jira because it's so slow and complex.",
        author="test_user",
        url="https://reddit.com/r/saas/123",
        upvotes=150,
        comments_count=45,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
        channel="r/saas",
        subreddit="saas",
        sentiment_label="frustrated",
        sentiment_intensity=0.7,
        metadata={},
    )


@pytest.fixture
def hackernews_post():
    """Create a sample HN post."""
    return ScrapedPost(
        id="test_hn_1",
        source="hackernews",
        title="Show HN: Fast project management tool",
        body="Built this because all existing tools are slow.",
        author="test_user",
        url="https://news.ycombinator.com/item?id=123",
        upvotes=50,
        comments_count=20,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        channel="hn/show",
        metadata={},
    )


@pytest.fixture
def g2_post():
    """Create a sample G2 review post."""
    return ScrapedPost(
        id="test_g2_1",
        source="g2",
        title="G2 Review",
        body="Terrible experience, willing to pay for something better",
        author="test_user",
        url="https://g2.com/products/tool/reviews/1",
        upvotes=5,
        comments_count=0,
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
        channel="g2/tool",
        metadata={"star_rating": 1},
    )


@pytest.fixture
def pain_score():
    """Create a sample pain score."""
    return PainScore(
        score=0.8,
        reasoning="Strong frustration with existing tools",
        detected_problems=["Slow performance", "Complex interface"],
        suggested_solutions=["Faster alternatives", "Simpler UI"],
        validation_score=0.7,
        engagement_score=0.5,
        recency_score=0.8,
        composite_value=0.75,
        sentiment_label="frustrated",
        sentiment_intensity=0.8,
    )


def test_engagement_norm_reddit(reddit_post):
    """Test engagement normalization for Reddit posts."""
    score = calculate_engagement_norm(reddit_post)

    assert 0.0 <= score <= 1.0
    assert score > 0.5, (
        "Reddit post with 150 upvotes and 45 comments should have high engagement"
    )


def test_engagement_norm_hackernews(hackernews_post):
    """Test engagement normalization for HN posts."""
    score = calculate_engagement_norm(hackernews_post)

    assert 0.0 <= score <= 1.0
    assert score > 0, "HN post with engagement should have positive score"


def test_engagement_norm_g2(g2_post):
    """Test engagement normalization for G2 reviews."""
    score = calculate_engagement_norm(g2_post)

    assert 0.0 <= score <= 1.0
    assert score > 0.5, "G2 review with 1-star rating should have high engagement score"


def test_recency_score_today():
    """Test recency score for today's post."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="Test",
        body="Test",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(timezone.utc),
    )
    score = calculate_recency_score(post)
    assert score == 1.0


def test_recency_score_week():
    """Test recency score for post from this week."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="Test",
        body="Test",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    score = calculate_recency_score(post)
    assert score == 0.8


def test_recency_score_month():
    """Test recency score for post from this month."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="Test",
        body="Test",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(timezone.utc) - timedelta(days=20),
    )
    score = calculate_recency_score(post)
    assert score == 0.5


def test_recency_score_old():
    """Test recency score for very old post."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="Test",
        body="Test",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(timezone.utc) - timedelta(days=100),
    )
    score = calculate_recency_score(post)
    assert score == 0.0


def test_market_signal_high():
    """Test market signal with high-intent keywords."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="Willing to pay for SaaS tool",
        body="Looking for B2B API subscription",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(),
    )
    score = calculate_market_signal(post)
    assert score > 0.5, "Post with high-intent keywords should have high market signal"


def test_market_signal_medium():
    """Test market signal with medium-intent keywords."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="Alternative to Jira",
        body="Looking for better tool",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(),
    )
    score = calculate_market_signal(post)
    assert 0.0 <= score <= 1.0


def test_market_signal_low():
    """Test market signal with low-intent keywords."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="How do I manage projects",
        body="Tutorial needed",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(),
    )
    score = calculate_market_signal(post)
    assert score < 0.5, "Post with low-intent keywords should have lower market signal"


def test_extract_key_terms():
    """Test key term extraction from post."""
    post = ScrapedPost(
        id="test",
        source="reddit",
        title="Project management tool frustration",
        body="I hate slow SaaS tools for startups",
        author="test",
        url="http://test.com",
        upvotes=0,
        comments_count=0,
        created_at=datetime.now(),
    )
    terms = extract_key_terms(post)
    assert isinstance(terms, list)
    assert len(terms) > 0
    assert any("project" in term.lower() for term in terms)


def test_compute_opportunity_score_basic(reddit_post, pain_score, storage):
    """Test basic opportunity score computation."""
    score = compute_opportunity_score(reddit_post, pain_score, storage)

    assert score.final_score >= 0.0
    assert score.final_score <= 1.0
    assert score.post_id == reddit_post.id
    assert score.source == reddit_post.source

    assert hasattr(score, "pain_intensity")
    assert hasattr(score, "engagement_norm")
    assert hasattr(score, "validation_evidence")
    assert hasattr(score, "sentiment_intensity")
    assert hasattr(score, "recency")
    assert hasattr(score, "trend_momentum")
    assert hasattr(score, "market_signal")
    assert hasattr(score, "cross_source_bonus")


def test_compute_opportunity_score_weights(reddit_post, pain_score, storage):
    """Test opportunity score with custom weights."""
    custom_weights = {
        "pain_intensity": 0.5,
        "engagement_norm": 0.1,
        "validation_evidence": 0.1,
        "sentiment_intensity": 0.1,
        "recency": 0.05,
        "trend_momentum": 0.05,
        "market_signal": 0.1,
    }

    score = compute_opportunity_score(
        reddit_post, pain_score, storage, weights=custom_weights
    )
    assert score.weights == custom_weights


def test_scoring_module_compute_score(reddit_post, pain_score, storage):
    """Test ScoringModule.compute_score method."""
    module = ScoringModule(storage)
    score = module.compute_score(reddit_post, pain_score)

    assert score.final_score >= 0.0
    assert score.final_score <= 1.0


def test_scoring_module_get_top_opportunities(storage, reddit_post, pain_score):
    """Test ScoringModule.get_top_opportunities method."""
    storage.save_post(reddit_post)
    storage.save_signal(reddit_post.id, pain_score)

    module = ScoringModule(storage)
    score = module.compute_score(reddit_post, pain_score)
    storage.save_opportunity_score(score)

    top_opportunities = module.get_top_opportunities(limit=10, min_score=0.0)

    assert len(top_opportunities) >= 1
    assert top_opportunities[0].post_id == reddit_post.id


def test_trend_momentum_with_insufficient_data(reddit_post, storage):
    """Test trend momentum defaults to 0.5 with insufficient data."""
    score = calculate_trend_momentum(reddit_post, storage)
    assert score == 0.5


def test_cross_source_bonus(storage, reddit_post, pain_score):
    """Test cross-source bonus calculation."""
    storage.save_post(reddit_post)

    hn_post = ScrapedPost(
        id="test_hn_similar",
        source="hackernews",
        title="Project management tool frustration",
        body="Similar content about project management",
        author="test2",
        url="http://test2.com",
        upvotes=10,
        comments_count=5,
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        channel="hn/show",
        metadata={},
    )
    storage.save_post(hn_post)

    bonus = calculate_cross_source_bonus(reddit_post, storage)
    assert bonus >= 0.0


def test_weights_sum_to_one():
    """Test that default weights sum to approximately 1.0."""
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected 1.0"
