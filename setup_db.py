# setup_db.py
"""Create a placeholder SQLite database `mediassist.db` with the schema required for SQL RAG.

Tables:
- claims(id INTEGER PRIMARY KEY, department TEXT, status TEXT, amount REAL, date TEXT)
- maintenance_tickets(id INTEGER PRIMARY KEY, category TEXT, issue_type TEXT, status TEXT)

The script also inserts a few sample rows for quick testing.
"""

import os
import sqlite3

# Path to DB (inside the data folder of the project)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "mediassist.db")

# Ensure the data directory exists
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Create tables
cur.execute("""
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department TEXT,
    status TEXT,
    amount REAL,
    date TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS maintenance_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    issue_type TEXT,
    status TEXT
);
""")

# Insert sample data (feel free to add more)
cur.executemany(
    "INSERT INTO claims (department, status, amount, date) VALUES (?, ?, ?, ?)",
    [
        ("billing", "escalated", 1200.50, "2023-04-15"),
        ("billing", "resolved", 800.00, "2023-04-10"),
        ("clinical", "pending", 300.00, "2023-04-12"),
    ],
)

cur.executemany(
    "INSERT INTO maintenance_tickets (category, issue_type, status) VALUES (?, ?, ?)",
    [
        ("MRI", "calibration", "open"),
        ("X‑Ray", "repair", "closed"),
        ("Ventilator", "inspection", "open"),
    ],
)

conn.commit()
conn.close()

print(f"Database created at {DB_PATH}")
