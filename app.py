import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import Flask, request, redirect, url_for, render_template, Response

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
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


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sex_label(code: str) -> str:
    return {"F": "Female", "M": "Male", "O": "Other / Prefer not to say"}.get(code, "—")


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
    "weekday": weekday
})
    return entries


# ---- v0 estimation model (UK Biobank, Sanchez-Lastra et al., 2021) ----
MODEL = [
    # (min_flights_inclusive, max_flights_inclusive_or_None, label, all_cause_hr, cvd_hr, rmst_days)
    (0, 0, "0", 1.00, 1.00, 0.0),
    (1, 5, "1–5", 1.01, 1.14, -27.43),
    (6, 10, "6–10", 0.91, 1.08, 45.73),
    (11, 15, "11–15", 0.92, 1.05, 55.79),
    (16, None, "≥16", 0.93, 1.04, 41.77),
]


def estimate_from_avg(avg_flights: float) -> dict:
    flights = max(0.0, avg_flights)
    chosen = MODEL[0]
    for (mn, mx, label, hr_all, hr_cvd, rmst) in MODEL:
        if mx is None:
            if flights >= mn:
                chosen = (mn, mx, label, hr_all, hr_cvd, rmst)
        else:
            if mn <= flights <= mx:
                chosen = (mn, mx, label, hr_all, hr_cvd, rmst)
                break

    _, _, label, hr_all, hr_cvd, rmst = chosen
    all_cause_reduction = (1.0 - hr_all) * 100.0
    cvd_reduction = (1.0 - hr_cvd) * 100.0
    life_days_gained = max(0.0, rmst)

    return {
        "category": label,
        "all_cause_reduction_pct": all_cause_reduction,
        "cvd_reduction_pct": cvd_reduction,
        "life_days_gained": life_days_gained,
    }


def compute_stats(entries: list[dict]) -> dict:
    days_tracked = len(entries)
    total_climbs = sum(e["climbs"] for e in entries) if entries else 0
    active_days = sum(1 for e in entries if e["climbs"] > 0) if entries else 0
    avg_per_day = (total_climbs / days_tracked) if days_tracked else 0.0
    consistency = (active_days / days_tracked * 100.0) if days_tracked else 0.0

    max_day = max((e["climbs"] for e in entries), default=0)
    avg_vs_max_pct = (avg_per_day / max_day * 100.0) if max_day > 0 else 0.0

    est = estimate_from_avg(avg_per_day)

    return {
        "days_tracked": days_tracked,
        "total_climbs": total_climbs,
        "active_days": active_days,
        "avg_per_day": avg_per_day,
        "consistency": consistency,
        "max_day": max_day,
        "avg_vs_max_pct": avg_vs_max_pct,
        "model_category": est["category"],
        "life_days_gained": est["life_days_gained"],
        "all_cause_reduction_pct": est["all_cause_reduction_pct"],
        "cvd_reduction_pct": est["cvd_reduction_pct"],
    }

def weekly_summary(entries: list[dict], weeks: int = 8) -> list[dict]:
    buckets: dict[tuple[int, int], int] = {}

    for e in entries:
        if e.get("dt") is None:
            continue

        iso_year, iso_week, _ = e["dt"].isocalendar()
        key = (iso_year, iso_week)
        buckets[key] = buckets.get(key, 0) + int(e["climbs"])

    keys_sorted = sorted(buckets.keys(), reverse=True)[:weeks]

    rows = []
    for (y, w) in keys_sorted:
        rows.append({
            "label": f"{y}-W{w:02d}",
            "total": buckets[(y, w)]
        })

    return rows


def monthly_summary(entries: list[dict], months: int = 12) -> list[dict]:
    buckets: dict[tuple[int, int], int] = {}

    for e in entries:
        if e.get("dt") is None:
            continue

        y = e["dt"].year
        m = e["dt"].month

        key = (y, m)
        buckets[key] = buckets.get(key, 0) + int(e["climbs"])

    keys_sorted = sorted(buckets.keys(), reverse=True)[:months]

    rows = []
    for (y, m) in keys_sorted:
        rows.append({
            "label": f"{y}-{m:02d}",
            "total": buckets[(y, m)]
        })

    return rows


def add_bar_widths(rows: list[dict]) -> list[dict]:
    max_total = max((r["total"] for r in rows), default=0)

    for r in rows:
        if max_total > 0:
            r["bar_pct"] = r["total"] / max_total * 100
        else:
            r["bar_pct"] = 0

    return rows

init_db()


@app.get("/")
def index():
    profile = load_profile()
    entries_sorted = load_entries()
    stats = compute_stats(entries_sorted)

    weekly = add_bar_widths(weekly_summary(entries_sorted, weeks=8))
    monthly = add_bar_widths(monthly_summary(entries_sorted, months=12))

    profile_summary = (
        f"Age: {profile['age'] or '—'}, "
        f"Weight: {profile['weight'] or '—'} kg, "
        f"Height: {profile['height'] or '—'} cm, "
        f"Sex: {sex_label(profile['sex'])}"
    )

    return render_template(
        "index.html",
        title="StairLife Tracker",
        today_str=date.today().isoformat(),
        profile=profile,
        profile_summary=profile_summary,
        stats=stats,
        entries=entries_sorted,
        weekly=weekly,
        monthly=monthly,
    )



@app.post("/profile")
def save_profile():
    age = (request.form.get("age") or "").strip()
    weight = (request.form.get("weight") or "").strip()
    height = (request.form.get("height") or "").strip()
    sex = (request.form.get("sex") or "").strip()

    with get_conn() as conn:
        conn.execute(
            "UPDATE profile SET age = ?, weight = ?, height = ?, sex = ? WHERE id = 1",
            (age, weight, height, sex),
        )

    return redirect(url_for("index"))


@app.post("/entry")
def save_entry():
    entry_date = (request.form.get("entry_date") or "").strip()
    climbs = safe_int((request.form.get("climbs") or "").strip(), default=0)

    if climbs < 0:
        climbs = 0

    if entry_date:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO entries (entry_date, climbs)
                VALUES (?, ?)
                ON CONFLICT(entry_date) DO UPDATE SET climbs = excluded.climbs
                """,
                (entry_date, climbs),
            )

    return redirect(url_for("index"))


@app.post("/entry/delete")
def delete_entry():
    entry_date = (request.form.get("entry_date") or "").strip()

    if entry_date:
        with get_conn() as conn:
            conn.execute(
                "DELETE FROM entries WHERE entry_date = ?",
                (entry_date,),
            )

    return redirect(url_for("index"))


@app.get("/export.csv")
def export_csv():
    entries = load_entries()  # already sorted DESC
    lines = ["date,year,month,weekday,climbs"]
    for e in entries:
        # ensure commas don't break CSV (we only have simple values here)
        lines.append(f'{e["date"]},{e["year"]},{e["month"]},{e["weekday"]},{e["climbs"]}')
    csv_text = "\n".join(lines) + "\n"
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=stairlife_export.csv"},
    )
