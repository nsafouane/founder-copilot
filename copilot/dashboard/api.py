import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Founder Co-Pilot Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv(
    "COPILOT_DB_PATH", "/root/.openclaw/workspace/founder-copilot/copilot.db"
)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
async def root():
    return {"status": "ok", "message": "Founder Co-Pilot API is running"}


@app.get("/signals")
async def get_signals(
    limit: int = 50,
    min_score: float = 0.5,
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        where_conditions = ["os.final_score >= ?"]
        params = [min_score]

        if source:
            where_conditions.append("os.source = ?")
            params.append(source)

        if sentiment:
            where_conditions.append("p.sentiment_label = ?")
            params.append(sentiment)

        where_clause = " AND ".join(where_conditions)

        query = f"""
        SELECT os.*, p.title, p.url, p.author, p.display_channel, p.sentiment_label as post_sentiment,
               s.sentiment_label as signal_sentiment, s.sentiment_intensity, s.reasoning
        FROM opportunity_scores os
        JOIN raw_posts p ON os.post_id = p.id
        LEFT JOIN signals s ON os.post_id = s.post_id
        WHERE {where_clause}
        ORDER BY os.final_score DESC
        LIMIT ?
        """

        params.append(limit)
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(
                {
                    "post_id": row["post_id"],
                    "source": row["source"],
                    "final_score": row["final_score"],
                    "pain_intensity": row["pain_intensity"],
                    "engagement_norm": row["engagement_norm"],
                    "validation_evidence": row["validation_evidence"],
                    "sentiment_intensity": row["sentiment_intensity"],
                    "recency": row["recency"],
                    "trend_momentum": row["trend_momentum"],
                    "market_signal": row["market_signal"],
                    "cross_source_bonus": row["cross_source_bonus"],
                    "title": row["title"],
                    "url": row["url"],
                    "author": row["author"],
                    "channel": row["display_channel"],
                    "sentiment_label": row["post_sentiment"] or row["signal_sentiment"],
                    "reasoning": row["reasoning"],
                    "computed_at": row["computed_at"],
                }
            )

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/personas")
async def get_personas(limit: int = 10, persona_type: Optional[str] = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        where_conditions = []
        params = []

        if persona_type:
            where_conditions.append("persona_type = ?")
            params.append(persona_type)

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        cursor.execute(
            f"""
            SELECT * FROM personas
            WHERE {where_clause}
            ORDER BY generated_at DESC
            LIMIT ?
        """,
            tuple(params + [limit]),
        )

        rows = cursor.fetchall()
        conn.close()

        personas = []
        for row in rows:
            personas.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "role": row["role"],
                    "company": row["company"],
                    "industry": row["industry"],
                    "pain_points": eval(row["pain_points"])
                    if row["pain_points"]
                    else [],
                    "personality": row["personality"],
                    "budget": row["budget"],
                    "preferred_communication": row["preferred_communication"],
                    "buying_triggers": eval(row["buying_triggers"])
                    if row["buying_triggers"]
                    else [],
                    "decision_maker": row["decision_maker"],
                    "persona_type": row["persona_type"],
                    "analysis": row["analysis"],
                    "opportunity_fit_score": row["opportunity_fit_score"],
                    "generated_at": row["generated_at"],
                }
            )

        return personas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/opportunities")
async def get_opportunities(limit: int = 50, min_score: float = 0.5):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT os.*, p.title, p.url, p.author, p.display_channel
        FROM opportunity_scores os
        JOIN raw_posts p ON os.post_id = p.id
        WHERE os.final_score >= ?
        ORDER BY os.final_score DESC
        LIMIT ?
        """

        cursor.execute(query, (min_score, limit))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads")
async def get_leads(limit: int = 50):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM leads ORDER BY intent_score DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        stats = {}
        cursor.execute("SELECT COUNT(*) FROM raw_posts")
        stats["total_posts"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM opportunity_scores WHERE final_score > 0.7"
        )
        stats["high_signal_opportunities"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leads")
        stats["total_leads"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM personas")
        stats["total_personas"] = cursor.fetchone()[0]

        conn.close()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
