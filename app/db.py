import os
import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "jobs.db")

def get_db():
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                validation_status TEXT,
                approval_status TEXT,
                raw_payload_json TEXT,
                timestamp_iso TEXT,
                whatsapp_message_id TEXT,
                posted_status TEXT,
                llm_extracted_json TEXT,
                override_used INTEGER,
                missing_fields_joined TEXT
            )
        ''')
        # Add job_hash column if it doesn't already exist
        try:
            db.execute('ALTER TABLE submissions ADD COLUMN job_hash TEXT')
        except sqlite3.OperationalError:
            pass
        # Add LLM columns defensively for existing tables during the migration
        try:
            db.execute('ALTER TABLE submissions ADD COLUMN llm_extracted_json TEXT')
            db.execute('ALTER TABLE submissions ADD COLUMN override_used INTEGER')
            db.execute('ALTER TABLE submissions ADD COLUMN missing_fields_joined TEXT')
        except sqlite3.OperationalError:
            pass
        db.execute('''
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                normalized_sender TEXT,
                message_text TEXT,
                command TEXT,
                result TEXT,
                submission_id TEXT,
                timestamp_iso TEXT
            )
        ''')
        db.commit()
    logger.info("SQLite Database initialized.")

def insert_bot_log(sender: str, normalized_sender: str, message_text: str, command: str, result: str, submission_id: str = None):
    with get_db() as db:
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        db.execute('''
            INSERT INTO bot_logs (sender, normalized_sender, message_text, command, result, submission_id, timestamp_iso)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (sender, normalized_sender, message_text, command, result, submission_id, timestamp_iso))
        db.commit()

def get_pending_submissions(limit: int = 10) -> List[Dict[str, Any]]:
    with get_db() as db:
        rows = db.execute('''
            SELECT submission_id, llm_extracted_json, timestamp_iso 
            FROM submissions 
            WHERE approval_status = 'PENDING' 
            ORDER BY timestamp_iso DESC 
            LIMIT ?
        ''', (limit,)).fetchall()
        return [dict(row) for row in rows]

def get_last_admin_interaction(normalized_sender: str) -> Optional[str]:
    """Returns the timestamp of the last inbound message from this admin."""
    with get_db() as db:
        row = db.execute('''
            SELECT timestamp_iso FROM bot_logs 
            WHERE normalized_sender = ? 
            ORDER BY timestamp_iso DESC LIMIT 1
        ''', (normalized_sender,)).fetchone()
        return row["timestamp_iso"] if row else None

def insert_submission(
    submission_id: str,
    validation_status: str,
    approval_status: str,
    raw_payload_json: str,
    timestamp_iso: str,
    job_hash: str = None,
    llm_extracted_json: str = None,
    override_used: int = 0,
    missing_fields_joined: str = None
):
    with get_db() as db:
        db.execute('''
            INSERT INTO submissions (
                submission_id, validation_status, approval_status, 
                raw_payload_json, timestamp_iso, job_hash, 
                llm_extracted_json, override_used, missing_fields_joined
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (submission_id, validation_status, approval_status, raw_payload_json, timestamp_iso, job_hash, llm_extracted_json, override_used, missing_fields_joined))
        db.commit()

def check_duplicate_hash(job_hash: str) -> bool:
    with get_db() as db:
        row = db.execute('SELECT 1 FROM submissions WHERE job_hash = ?', (job_hash,)).fetchone()
        return bool(row)

def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        row = db.execute('SELECT * FROM submissions WHERE submission_id = ?', (submission_id,)).fetchone()
        if row:
            return dict(row)
    return None

def update_submission_status(
    submission_id: str,
    approval_status: str = None,
    whatsapp_message_id: str = None,
    posted_status: str = None
):
    with get_db() as db:
        if approval_status:
            db.execute('UPDATE submissions SET approval_status = ? WHERE submission_id = ?', (approval_status, submission_id))
        if whatsapp_message_id:
            db.execute('UPDATE submissions SET whatsapp_message_id = ? WHERE submission_id = ?', (whatsapp_message_id, submission_id))
        if posted_status:
            db.execute('UPDATE submissions SET posted_status = ? WHERE submission_id = ?', (posted_status, submission_id))
        db.commit()

def update_submission_by_wa_id(
    whatsapp_message_id: str,
    posted_status: str
):
    with get_db() as db:
        db.execute('''
            UPDATE submissions 
            SET posted_status = ? 
            WHERE whatsapp_message_id = ?
        ''', (posted_status, whatsapp_message_id))
        db.commit()

init_db()
