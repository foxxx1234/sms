import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, '..', 'events.db')

_schema = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    port TEXT,
    event_type TEXT NOT NULL,
    phone TEXT,
    details TEXT
);
"""

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_schema)
    conn.commit()
    conn.close()

def log_event(event_type: str, port: str = None, phone: str = None, details: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO events (timestamp, port, event_type, phone, details) VALUES (?, ?, ?, ?, ?)",
        (ts, port, event_type, phone, details),
    )
    conn.commit()
    conn.close()
