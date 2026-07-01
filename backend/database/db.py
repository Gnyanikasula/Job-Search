"""
database/db.py — SQLite connection and all query helpers
Keys can come from DB (entered via UI) OR from environment variables.
Environment variables take priority — used for Docker/HuggingFace secrets.
"""
import os
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from .models import CREATE_TABLES_SQL

# Support both Docker volume mount and local run
_db_env = os.environ.get("DB_PATH", "").strip()
DB_PATH = Path(_db_env) if _db_env else Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(CREATE_TABLES_SQL)
        cur = conn.execute("SELECT COUNT(*) FROM profiles")
        if cur.fetchone()[0] == 0:
            conn.execute("""
                INSERT INTO profiles (id, name, location, country)
                VALUES ('gnyani', 'Gnyani Kasula', 'London, UK', 'UK'),
                       ('friend', 'Friend', 'India', 'India')
            """)
        conn.commit()


# ── profiles ──────────────────────────────────────────────────────────────────

def get_profile(profile_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return dict(row) if row else None


def update_profile(profile_id: str, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [profile_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE profiles SET {fields} WHERE id = ?", vals)
        conn.commit()


def get_all_profiles() -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM profiles").fetchall()]


# ── api keys ──────────────────────────────────────────────────────────────────

def get_keys(profile_id: str) -> dict:
    """
    Returns API keys. Environment variables take priority over DB values.
    This means HuggingFace Spaces secrets work automatically.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE profile_id = ?", (profile_id,)
        ).fetchone()
        db_keys = dict(row) if row else {}

    return {
        "profile_id": profile_id,
        "gemini_key":  os.environ.get("GEMINI_API_KEY")  or db_keys.get("gemini_key", ""),
        "groq_key":    os.environ.get("GROQ_API_KEY")    or db_keys.get("groq_key", ""),
        "serper_key":  os.environ.get("SERPER_API_KEY")  or db_keys.get("serper_key", ""),
    }


def save_keys(profile_id: str, gemini_key="", groq_key="", serper_key=""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO api_keys (profile_id, gemini_key, groq_key, serper_key, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(profile_id) DO UPDATE SET
                gemini_key  = excluded.gemini_key,
                groq_key    = excluded.groq_key,
                serper_key  = excluded.serper_key,
                updated_at  = excluded.updated_at
        """, (profile_id, gemini_key, groq_key, serper_key))
        conn.commit()


# ── jobs ──────────────────────────────────────────────────────────────────────

def make_fingerprint(company: str, title: str, location: str) -> str:
    raw = f"{company}|{title}|{location}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()


def job_exists_recent(fingerprint: str, profile_id: str, hours: int = 24) -> bool:
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with get_conn() as conn:
        row = conn.execute("""
            SELECT 1 FROM jobs
            WHERE id = ? AND profile_id = ? AND fetched_at > ?
        """, (fingerprint, profile_id, cutoff)).fetchone()
        return row is not None


def upsert_job(profile_id: str, job: dict) -> bool:
    """Insert job if not seen in last 24h. Returns True if inserted."""
    fp = make_fingerprint(
        job.get("company", ""), job.get("title", ""), job.get("location", "")
    )
    if job_exists_recent(fp, profile_id):
        return False
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO jobs
                (id, profile_id, title, company, location, source, url,
                 description, date_posted, fetched_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'New')
        """, (
            fp, profile_id,
            job.get("title", ""), job.get("company", ""),
            job.get("location", ""), job.get("source", ""),
            job.get("job_url", ""), job.get("description", "")[:5000],
            job.get("date_posted", ""),
        ))
        conn.commit()
    return True


def get_jobs(profile_id: str, status: str | None = None,
             limit: int = 200, days: int = 7) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        if status:
            rows = conn.execute("""
                SELECT * FROM jobs
                WHERE profile_id = ? AND status = ? AND fetched_at > ?
                ORDER BY score DESC, fetched_at DESC LIMIT ?
            """, (profile_id, status, cutoff, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM jobs
                WHERE profile_id = ? AND fetched_at > ?
                ORDER BY score DESC, fetched_at DESC LIMIT ?
            """, (profile_id, cutoff, limit)).fetchall()
        return [dict(r) for r in rows]


def update_job_status(job_id: str, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        conn.commit()


def update_job_score(job_id: str, score: int, score_data: dict):
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET score = ?, score_data = ? WHERE id = ?",
            (score, json.dumps(score_data), job_id)
        )
        conn.commit()


# ── score cache ───────────────────────────────────────────────────────────────

def get_cached_score(fingerprint: str, profile_id: str, max_age_days: int = 7) -> dict | None:
    cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
    with get_conn() as conn:
        row = conn.execute("""
            SELECT * FROM scores
            WHERE fingerprint = ? AND profile_id = ? AND scored_at > ?
        """, (fingerprint, profile_id, cutoff)).fetchone()
        if row:
            d = dict(row)
            try:
                d["breakdown"] = json.loads(d.get("breakdown", "{}"))
            except Exception:
                d["breakdown"] = {}
            return d
        return None


def cache_score(fingerprint: str, profile_id: str, score: int, breakdown: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO scores
                (fingerprint, profile_id, score, breakdown, scored_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (fingerprint, profile_id, score, json.dumps(breakdown)))
        conn.commit()


# ── search log ────────────────────────────────────────────────────────────────

def log_search(profile_id: str, trigger: str, jobs_found: int,
               jobs_new: int, error: str = ""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO search_log (profile_id, trigger, jobs_found, jobs_new, error)
            VALUES (?, ?, ?, ?, ?)
        """, (profile_id, trigger, jobs_found, jobs_new, error))
        conn.commit()


def get_last_search(profile_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT * FROM search_log WHERE profile_id = ?
            ORDER BY ran_at DESC LIMIT 1
        """, (profile_id,)).fetchone()
        return dict(row) if row else None


def update_job_description(job_id: str, description: str):
    """Update the description of an existing job (after JD fetch)."""
    with get_conn() as conn:
        conn.execute("UPDATE jobs SET description = ? WHERE id = ?",
                     (description[:4000], job_id))
        conn.commit()
