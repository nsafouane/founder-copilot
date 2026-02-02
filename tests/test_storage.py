import os
import pytest
from datetime import datetime, timezone
from copilot.providers.storage.sqlite_provider import SQLiteProvider
from copilot.models.schemas import ScrapedPost, PainScore

DB_PATH = "test_founder.db"

@pytest.fixture
def storage():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    provider = SQLiteProvider(db_path=DB_PATH)
    provider.initialize()
    yield provider
    provider.close()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_sqlite_save_and_get_post(storage):
    post = ScrapedPost(
        id="t3_12345",
        source="reddit",
        title="Need help with accounting",
        body="I hate manually entering invoices",
        author="founder_bot",
        url="https://reddit.com/r/saas/comments/12345",
        upvotes=10,
        comments_count=5,
        created_at=datetime.now(timezone.utc),
        subreddit="saas",
        metadata={"flair": "Question"}
    )
    
    storage.save_post(post)
    posts = storage.get_posts(limit=1)
    
    assert len(posts) == 1
    assert posts[0].id == post.id
    assert posts[0].title == post.title
    assert posts[0].metadata["flair"] == "Question"

def test_sqlite_save_signal(storage):
    post_id = "t3_12345"
    pain_info = PainScore(
        score=0.9,
        reasoning="High frustration expressed",
        detected_problems=["manual data entry", "invoice errors"],
        suggested_solutions=["automated invoice parser"],
        validation_score=0.8,
        engagement_score=0.5,
        recency_score=1.0,
        composite_value=0.85
    )
    
    # Save post first due to foreign key (though SQLite doesn't always enforce it unless configured)
    post = ScrapedPost(
        id=post_id,
        source="reddit",
        title="Test",
        body="Test",
        author="test",
        url="test",
        upvotes=1,
        comments_count=1,
        created_at=datetime.now(timezone.utc)
    )
    storage.save_post(post)
    
    storage.save_signal(post_id, pain_info)
    
    # Verify by direct query
    conn = storage._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signals WHERE post_id = ?", (post_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row["score"] == 0.9
    assert "manual data entry" in row["detected_problems"]
