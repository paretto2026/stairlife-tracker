import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "stairlife.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                age TEXT,
                weight TEXT,
                height TEXT,
                sex TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                entry_date TEXT PRIMARY KEY,
                climbs INTEGER NOT NULL
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO profile (id, age, weight, height, sex)
            VALUES (1, '', '', '', '')
        """)


def load_profile() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT age, weight, height, sex FROM profile WHERE id = 1").fetchone()
        if not row:
            return {"age": "", "weight": "", "height": "", "sex": ""}
        return {"age": row["age"], "weight": row["weight"], "height": row["height"], "sex": row["sex"]}


def load_entries() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT entry_date, climbs FROM entries ORDER BY entry_date DESC"
        ).fetchall()

    entries: list[dict] = []
    for r in rows:
        d = r["entry_date"]
        climbs = int(r["climbs"])
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            year = dt.year
            month = dt.strftime("%b")
            weekday = dt.strftime("%a")
        except ValueError:
            dt = None
            year = ""
            month = ""
            weekday = ""
        entries.append({
            "date": d,
            "dt": dt,
            "climbs": climbs,
            "year": year,
            "month": month,
            "weekday": weekday,
        })
    return entries


def update_profile(age: str, weight: str, height: str, sex: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE profile SET age = ?, weight = ?, height = ?, sex = ? WHERE id = 1",
            (age, weight, height, sex),
        )


def upsert_entry(entry_date: str, climbs: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO entries (entry_date, climbs)
            VALUES (?, ?)
            ON CONFLICT(entry_date) DO UPDATE SET climbs = excluded.climbs
            """,
            (entry_date, climbs),
        )


def remove_entry(entry_date: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM entries WHERE entry_date = ?",
            (entry_date,),
        )
