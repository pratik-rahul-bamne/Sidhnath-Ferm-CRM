import sqlite3
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

# Determine directory paths for normal vs. PyInstaller frozen EXE
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR

DB_PATH = os.environ.get("DB_PATH", os.path.join(APP_DIR, "siddhanth_firm.db"))

# Register adapters/converters so DATE columns come back as Python date objects
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("DATE", lambda b: date.fromisoformat(b.decode()))
sqlite3.register_converter("TIMESTAMP", lambda b: datetime.fromisoformat(b.decode()) if b else None)


def get_db():
    """Return a sqlite3 connection with Row dict-like access and type detection."""
    conn = sqlite3.connect(
        DB_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables from database.sql if they don't exist."""
    conn = get_db()
    try:
        sql_file = os.path.join(BUNDLE_DIR, "database.sql")
        if not os.path.exists(sql_file):
            sql_file = os.path.join(APP_DIR, "database.sql")
        with open(sql_file, "r", encoding="utf-8") as f:
            sql = f.read()
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
