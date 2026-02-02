import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import StorageProvider
from ...models.schemas import ScrapedPost, PainScore

class SQLiteProvider(StorageProvider):
    """SQLite implementation of the StorageProvider."""

    def __init__(self, db_path: str = "founder_copilot.db"):
        self.db_path = db_path
        self._conn = None

    @property
    def name(self) -> str:
        return "sqlite"

    def _get_connection(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def initialize(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Raw Posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_posts (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                author TEXT,
                url TEXT,
                upvotes INTEGER,
                comments_count INTEGER,
                created_at TEXT,
                subreddit TEXT,
                metadata TEXT
            )
        """)

        # Signals (Analysis) table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                post_id TEXT PRIMARY KEY,
                score REAL,
                reasoning TEXT,
                detected_problems TEXT,
                suggested_solutions TEXT,
                validation_score REAL,
                engagement_score REAL,
                recency_score REAL,
                composite_value REAL,
                analyzed_at TEXT,
                FOREIGN KEY (post_id) REFERENCES raw_posts (id)
            )
        """)
        
        # Leads table (Placeholder for future phases)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                contact_info TEXT,
                intent_score REAL,
                status TEXT,
                FOREIGN KEY (post_id) REFERENCES raw_posts (id)
            )
        """)
        
        conn.commit()

    def save_post(self, post: ScrapedPost) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO raw_posts 
            (id, source, title, body, author, url, upvotes, comments_count, created_at, subreddit, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post.id, post.source, post.title, post.body, post.author, 
            post.url, post.upvotes, post.comments_count, post.created_at.isoformat(), 
            post.subreddit, json.dumps(post.metadata)
        ))
        conn.commit()

    def save_signal(self, post_id: str, pain_info: PainScore) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO signals 
            (post_id, score, reasoning, detected_problems, suggested_solutions, 
             validation_score, engagement_score, recency_score, composite_value, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id, pain_info.score, pain_info.reasoning, 
            json.dumps(pain_info.detected_problems), json.dumps(pain_info.suggested_solutions),
            pain_info.validation_score, pain_info.engagement_score, pain_info.recency_score,
            pain_info.composite_value, datetime.now().isoformat()
        ))
        conn.commit()

    def get_posts(self, limit: int = 100) -> List[ScrapedPost]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM raw_posts ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        posts = []
        for row in rows:
            posts.append(ScrapedPost(
                id=row["id"],
                source=row["source"],
                title=row["title"],
                body=row["body"],
                author=row["author"],
                url=row["url"],
                upvotes=row["upvotes"],
                comments_count=row["comments_count"],
                created_at=datetime.fromisoformat(row["created_at"]),
                subreddit=row["subreddit"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            ))
        return posts

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
