import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("SHUMWAY_DB", str(Path(__file__).parent.parent / "shumway.db"))

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    with get_connection() as conn:
        conn.executescript(schema_path.read_text())
    print(f"[db] Database initialised at {DB_PATH}")

if __name__ == "__main__":
    init_db()