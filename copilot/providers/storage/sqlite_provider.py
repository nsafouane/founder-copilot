import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import StorageProvider
from ...models.schemas import (
    ScrapedPost,
    PainScore,
    Lead,
    ValidationReport,
    OpportunityScore,
)


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

        # Leads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                author TEXT,
                content_snippet TEXT,
                intent_score REAL,
                contact_url TEXT,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY (post_id) REFERENCES raw_posts (id)
            )
        """)

        # Validation Reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_reports (
                post_id TEXT PRIMARY KEY,
                idea_summary TEXT,
                market_size_estimate TEXT,
                competitors TEXT,
                swot_analysis TEXT,
                validation_verdict TEXT,
                next_steps TEXT,
                generated_at TEXT,
                FOREIGN KEY (post_id) REFERENCES raw_posts (id)
            )
        """)

        conn.commit()

        # Migration Logic: Check and add columns if they don't exist
        # Example for 'leads' table: add 'author' if not exists.
        # This is a simplified example; a full migration system would be more robust.
        self._add_column_if_not_exists(cursor, "leads", "author", "TEXT")
        self._add_column_if_not_exists(cursor, "leads", "content_snippet", "TEXT")
        self._add_column_if_not_exists(cursor, "leads", "intent_score", "REAL")
        self._add_column_if_not_exists(cursor, "leads", "contact_url", "TEXT")
        self._add_column_if_not_exists(cursor, "leads", "status", "TEXT")
        self._add_column_if_not_exists(cursor, "leads", "created_at", "TEXT")

        self._add_column_if_not_exists(cursor, "raw_posts", "metadata", "TEXT")

        # Add columns for PainScore if they don't exist
        self._add_column_if_not_exists(cursor, "signals", "validation_score", "REAL")
        self._add_column_if_not_exists(cursor, "signals", "engagement_score", "REAL")
        self._add_column_if_not_exists(cursor, "signals", "recency_score", "REAL")
        self._add_column_if_not_exists(cursor, "signals", "composite_value", "REAL")
        self._add_column_if_not_exists(cursor, "signals", "analyzed_at", "TEXT")

        # Phase 1 Migrations: Add new columns for multi-platform support
        # raw_posts: Add channel and sentiment fields
        self._add_column_if_not_exists(cursor, "raw_posts", "channel", "TEXT")
        self._add_column_if_not_exists(cursor, "raw_posts", "sentiment_label", "TEXT")
        self._add_column_if_not_exists(
            cursor, "raw_posts", "sentiment_intensity", "REAL DEFAULT 0.0"
        )

        # signals: Add sentiment fields
        self._add_column_if_not_exists(cursor, "signals", "sentiment_label", "TEXT")
        self._add_column_if_not_exists(
            cursor, "signals", "sentiment_intensity", "REAL DEFAULT 0.0"
        )

        # leads: Add source and sentiment
        self._add_column_if_not_exists(
            cursor, "leads", "source", 'TEXT DEFAULT "reddit"'
        )
        self._add_column_if_not_exists(cursor, "leads", "sentiment_label", "TEXT")
        self._add_column_if_not_exists(
            cursor, "leads", "sentiment_intensity", "REAL DEFAULT 0.0"
        )
        self._add_column_if_not_exists(cursor, "leads", "verified_profiles", "TEXT")

        # validation_reports: Add source and cross-source fields
        self._add_column_if_not_exists(
            cursor, "validation_reports", "source", 'TEXT DEFAULT "reddit"'
        )
        self._add_column_if_not_exists(
            cursor, "validation_reports", "corroborating_sources", "TEXT"
        )
        self._add_column_if_not_exists(
            cursor, "validation_reports", "corroborating_post_ids", "TEXT"
        )

        # Create opportunity_scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunity_scores (
                post_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                final_score REAL NOT NULL,
                pain_intensity REAL DEFAULT 0.0,
                engagement_norm REAL DEFAULT 0.0,
                validation_evidence REAL DEFAULT 0.0,
                sentiment_intensity REAL DEFAULT 0.0,
                recency REAL DEFAULT 0.0,
                trend_momentum REAL DEFAULT 0.5,
                market_signal REAL DEFAULT 0.0,
                cross_source_bonus REAL DEFAULT 0.0,
                dimensions TEXT,
                weights TEXT,
                computed_at TEXT,
                FOREIGN KEY (post_id) REFERENCES raw_posts (id)
            )
        """)

        # Create personas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                company TEXT,
                industry TEXT,
                pain_points TEXT,
                personality TEXT,
                budget TEXT,
                preferred_communication TEXT,
                buying_triggers TEXT,
                decision_maker TEXT,
                persona_type TEXT DEFAULT 'startup_founder',
                analysis TEXT,
                opportunity_fit_score REAL DEFAULT 0.0,
                generated_at TEXT
            )
        """)

        conn.commit()

    def _add_column_if_not_exists(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
        column_name: str,
        column_type: str,
    ):
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        if column_name not in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )
            print(f"Added column {column_name} to table {table_name}")  # For debugging

    def save_post(self, post: ScrapedPost) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO raw_posts 
            (id, source, title, body, author, url, upvotes, comments_count, created_at, subreddit, metadata, channel, sentiment_label, sentiment_intensity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                post.id,
                post.source,
                post.title,
                post.body,
                post.author,
                post.url,
                post.upvotes,
                post.comments_count,
                post.created_at.isoformat(),
                post.subreddit,
                json.dumps(post.metadata),
                post.channel,
                post.sentiment_label,
                post.sentiment_intensity,
            ),
        )
        conn.commit()

    def save_signal(self, post_id: str, pain_info: PainScore) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO signals 
            (post_id, score, reasoning, detected_problems, suggested_solutions, 
             validation_score, engagement_score, recency_score, composite_value, analyzed_at,
             sentiment_label, sentiment_intensity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                post_id,
                pain_info.score,
                pain_info.reasoning,
                json.dumps(pain_info.detected_problems),
                json.dumps(pain_info.suggested_solutions),
                pain_info.validation_score,
                pain_info.engagement_score,
                pain_info.recency_score,
                pain_info.composite_value,
                datetime.now().isoformat(),
                pain_info.sentiment_label,
                pain_info.sentiment_intensity,
            ),
        )
        conn.commit()

    def get_signal(self, post_id: str) -> Optional[PainScore]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals WHERE post_id = ?", (post_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return PainScore(
            score=row["score"],
            reasoning=row["reasoning"],
            detected_problems=json.loads(row["detected_problems"])
            if row["detected_problems"]
            else [],
            suggested_solutions=json.loads(row["suggested_solutions"])
            if row["suggested_solutions"]
            else [],
            validation_score=row["validation_score"] or 0.0,
            engagement_score=row["engagement_score"] or 0.0,
            recency_score=row["recency_score"] or 0.0,
            composite_value=row["composite_value"] or 0.0,
            sentiment_label=row["sentiment_label"]
            if "sentiment_label" in row.keys()
            else None,
            sentiment_intensity=row["sentiment_intensity"]
            if "sentiment_intensity" in row.keys()
            else 0.0,
        )

    def get_posts(
        self, limit: int = 100, source: Optional[str] = None
    ) -> List[ScrapedPost]:
        conn = self._get_connection()
        cursor = conn.cursor()

        if source:
            cursor.execute(
                "SELECT * FROM raw_posts WHERE source = ? ORDER BY created_at DESC LIMIT ?",
                (source, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM raw_posts ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        rows = cursor.fetchall()

        posts = []
        for row in rows:
            posts.append(
                ScrapedPost(
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
                    channel=row["channel"] if row["channel"] else None,
                    sentiment_label=row["sentiment_label"]
                    if row["sentiment_label"]
                    else None,
                    sentiment_intensity=row["sentiment_intensity"]
                    if row["sentiment_intensity"]
                    else 0.0,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
            )
        return posts

    def save_lead(self, lead: Lead) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        if lead.id:
            # Update existing lead
            cursor.execute(
                """
                UPDATE leads SET 
                    post_id = ?, source = ?, author = ?, content_snippet = ?, 
                    intent_score = ?, sentiment_label = ?, sentiment_intensity = ?, 
                    contact_url = ?, verified_profiles = ?, status = ?, created_at = ?
                WHERE id = ?
            """,
                (
                    lead.post_id,
                    lead.source,
                    lead.author,
                    lead.content_snippet,
                    lead.intent_score,
                    lead.sentiment_label,
                    lead.sentiment_intensity,
                    lead.contact_url,
                    json.dumps(lead.verified_profiles),
                    lead.status,
                    lead.created_at.isoformat(),
                    lead.id,
                ),
            )
        else:
            # Insert new lead
            cursor.execute(
                """
                INSERT INTO leads (post_id, source, author, content_snippet, intent_score, sentiment_label, sentiment_intensity, contact_url, verified_profiles, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    lead.post_id,
                    lead.source,
                    lead.author,
                    lead.content_snippet,
                    lead.intent_score,
                    lead.sentiment_label,
                    lead.sentiment_intensity,
                    lead.contact_url,
                    json.dumps(lead.verified_profiles),
                    lead.status,
                    lead.created_at.isoformat(),
                ),
            )
        conn.commit()

    def get_leads(self, limit: Optional[int] = 100) -> List[Lead]:
        conn = self._get_connection()
        cursor = conn.cursor()
        limit_sql = f"LIMIT {limit}" if limit is not None else ""
        cursor.execute(f"SELECT * FROM leads ORDER BY created_at DESC {limit_sql}")
        rows = cursor.fetchall()

        leads = []
        for row in rows:
            leads.append(
                Lead(
                    id=row["id"],
                    post_id=row["post_id"],
                    source=row["source"] if row["source"] else "reddit",
                    author=row["author"],
                    content_snippet=row["content_snippet"],
                    intent_score=row["intent_score"],
                    sentiment_label=row["sentiment_label"]
                    if row["sentiment_label"]
                    else None,
                    sentiment_intensity=row["sentiment_intensity"]
                    if row["sentiment_intensity"]
                    else 0.0,
                    contact_url=row["contact_url"],
                    verified_profiles=json.loads(row["verified_profiles"])
                    if "verified_profiles" in row.keys() and row["verified_profiles"]
                    else {},
                    status=row["status"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return leads

    def save_report(self, report: ValidationReport) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO validation_reports 
            (post_id, source, idea_summary, market_size_estimate, competitors, swot_analysis, 
             validation_verdict, next_steps, corroborating_sources, corroborating_post_ids, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                report.post_id,
                report.source,
                report.idea_summary,
                report.market_size_estimate,
                json.dumps(report.competitors),
                json.dumps(report.swot_analysis),
                report.validation_verdict,
                json.dumps(report.next_steps),
                json.dumps(report.corroborating_sources),
                json.dumps(report.corroborating_post_ids),
                report.generated_at.isoformat(),
            ),
        )
        conn.commit()

    def get_reports(self, limit: Optional[int] = None) -> List[ValidationReport]:
        conn = self._get_connection()
        cursor = conn.cursor()
        limit_sql = f"LIMIT {limit}" if limit is not None else ""
        cursor.execute(
            f"SELECT * FROM validation_reports ORDER BY generated_at DESC {limit_sql}"
        )
        rows = cursor.fetchall()

        reports = []
        for row in rows:
            reports.append(
                ValidationReport(
                    post_id=row["post_id"],
                    source=row["source"] if row["source"] else "reddit",
                    idea_summary=row["idea_summary"],
                    market_size_estimate=row["market_size_estimate"],
                    competitors=json.loads(row["competitors"]),
                    swot_analysis=json.loads(row["swot_analysis"]),
                    validation_verdict=row["validation_verdict"],
                    next_steps=json.loads(row["next_steps"]),
                    corroborating_sources=json.loads(
                        row["corroborating_sources"]
                        if row["corroborating_sources"]
                        else "[]"
                    ),
                    corroborating_post_ids=json.loads(
                        row["corroborating_post_ids"]
                        if row["corroborating_post_ids"]
                        else "[]"
                    ),
                    generated_at=datetime.fromisoformat(row["generated_at"]),
                )
            )
        return reports

    def get_post_by_id(self, post_id: str) -> Optional[ScrapedPost]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM raw_posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return ScrapedPost(
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
            channel=row["channel"] if row["channel"] else None,
            sentiment_label=row["sentiment_label"] if row["sentiment_label"] else None,
            sentiment_intensity=row["sentiment_intensity"]
            if row["sentiment_intensity"]
            else 0.0,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def save_opportunity_score(self, score: OpportunityScore) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO opportunity_scores 
            (post_id, source, final_score, pain_intensity, engagement_norm, validation_evidence, 
             sentiment_intensity, recency, trend_momentum, market_signal, cross_source_bonus, 
             dimensions, weights, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                score.post_id,
                score.source,
                score.final_score,
                score.pain_intensity,
                score.engagement_norm,
                score.validation_evidence,
                score.sentiment_intensity,
                score.recency,
                score.trend_momentum,
                score.market_signal,
                score.cross_source_bonus,
                json.dumps(score.dimensions),
                json.dumps(score.weights),
                score.computed_at.isoformat(),
            ),
        )
        conn.commit()

    def get_opportunity_scores(
        self, limit: int = 100, min_score: float = 0.0
    ) -> List[OpportunityScore]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM opportunity_scores 
            WHERE final_score >= ? 
            ORDER BY final_score DESC 
            LIMIT ?
        """,
            (min_score, limit),
        )
        rows = cursor.fetchall()

        scores = []
        for row in rows:
            scores.append(
                OpportunityScore(
                    post_id=row["post_id"],
                    source=row["source"],
                    final_score=row["final_score"],
                    pain_intensity=row["pain_intensity"],
                    engagement_norm=row["engagement_norm"],
                    validation_evidence=row["validation_evidence"],
                    sentiment_intensity=row["sentiment_intensity"],
                    recency=row["recency"],
                    trend_momentum=row["trend_momentum"],
                    market_signal=row["market_signal"],
                    cross_source_bonus=row["cross_source_bonus"],
                    dimensions=json.loads(row["dimensions"]),
                    weights=json.loads(row["weights"]),
                    computed_at=datetime.fromisoformat(row["computed_at"]),
                )
            )
        return scores

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
