"""
database.py
───────────
PostgreSQL integration using psycopg2.
Stores the full enriched recipe JSON in a single JSONB column for
flexibility, plus a few indexed scalar columns for efficient history queries.

Environment variables required:
  DB_HOST      – default: localhost
  DB_PORT      – default: 5432
  DB_NAME      – default: recipes_db
  DB_USER      – default: postgres
  DB_PASSWORD  – required (no default)
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


# ── Connection factory ─────────────────────────────────────────────────────────

def _get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "recipes_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


# ── Schema creation ────────────────────────────────────────────────────────────

def init_db():
    """Create the recipes table if it doesn't already exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS recipes (
        id          SERIAL PRIMARY KEY,
        url         TEXT NOT NULL,
        title       TEXT,
        cuisine     TEXT,
        difficulty  TEXT,
        servings    INTEGER,
        data        JSONB NOT NULL,          -- full enriched recipe JSON
        created_at  TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS recipes_url_idx ON recipes (url);
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    finally:
        conn.close()


# ── Write ──────────────────────────────────────────────────────────────────────

def save_recipe(url: str, data: dict) -> int:
    """
    Insert a new recipe row and return the generated id.
    The full enriched dict is stored in the JSONB `data` column;
    scalar columns are also populated for fast list queries.
    """
    sql = """
    INSERT INTO recipes (url, title, cuisine, difficulty, servings, data)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id;
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                url,
                data.get("title"),
                data.get("cuisine"),
                data.get("difficulty"),
                data.get("servings"),
                json.dumps(data),
            ))
            row = cur.fetchone()
        conn.commit()
        return row[0]
    finally:
        conn.close()


# ── Read ───────────────────────────────────────────────────────────────────────

def get_all_recipes() -> list[dict]:
    """
    Return a summary list of all stored recipes for the history tab.
    Only fetches scalar columns (no heavy JSONB) for performance.
    """
    sql = """
    SELECT id, url, title, cuisine, difficulty, servings, created_at
    FROM recipes
    ORDER BY created_at DESC;
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        # Convert to plain dicts and serialise datetime
        result = []
        for row in rows:
            r = dict(row)
            if isinstance(r.get("created_at"), datetime):
                r["created_at"] = r["created_at"].isoformat()
            result.append(r)
        return result
    finally:
        conn.close()


def get_recipe_by_id(recipe_id: int) -> dict | None:
    """
    Fetch the full enriched recipe dict for a single id.
    Returns None if not found.
    """
    sql = "SELECT id, url, data FROM recipes WHERE id = %s;"
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (recipe_id,))
            row = cur.fetchone()
        if row is None:
            return None
        full = dict(row["data"])   # JSONB is auto-parsed by psycopg2
        full["id"]  = row["id"]
        full["url"] = row["url"]
        return full
    finally:
        conn.close()