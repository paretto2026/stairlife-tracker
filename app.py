import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import Flask, request, redirect, url_for

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
            month = dt.strftime("%b")    # Jan, Feb...
            weekday = dt.strftime("%a")  # Mon, Tue...
        except ValueError:
            year = ""
            month = ""
            weekday = ""
        entries.append({"date": d, "climbs": climbs, "year": year, "month": month, "weekday": weekday})
    return entries


# ---- v0 estimation model (UK Biobank, Sanchez-Lastra et al., 2021) ----
# Category thresholds are flights/day; we interpret "climbs" as flights for now.
MODEL = [
    # (min_flights_inclusive, max_flights_inclusive_or_None, label, all_cause_hr, cvd_hr, rmst_days)
    (0, 0, "0", 1.00, 1.00, 0.0),
    (1, 5, "1–5", 1.01, 1.14, -27.43),
    (6, 10, "6–10", 0.91, 1.08, 45.73),
    (11, 15, "11–15", 0.92, 1.05, 55.79),
    (16, None, "≥16", 0.93, 1.04, 41.77),
]


def estimate_from_avg(avg_flights: float) -> dict:
    # Find matching category for avg_flights
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
    life_days_gained = max(0.0, rmst)  # do not show negative as "gained"

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


# Initialize DB on startup
init_db()


@app.get("/")
def index():
    today_str = date.today().isoformat()

    profile = load_profile()
    entries_sorted = load_entries()
    stats = compute_stats(entries_sorted)

    rows_html = ""
    for e in entries_sorted:
        rows_html += f"""
          <tr>
            <td style="padding:8px; border-bottom:1px solid #eee;">{e["year"]}</td>
            <td style="padding:8px; border-bottom:1px solid #eee;">{e["month"]}</td>
            <td style="padding:8px; border-bottom:1px solid #eee;">{e["weekday"]}</td>
            <td style="padding:8px; border-bottom:1px solid #eee;">{e["date"]}</td>
            <td style="padding:8px; border-bottom:1px solid #eee; text-align:right;">{e["climbs"]}</td>
          </tr>
        """

    if not rows_html:
        rows_html = """
          <tr>
            <td colspan="5" style="padding:10px; color:#666;">No entries yet.</td>
          </tr>
        """

    profile_summary = (
        f"Age: {profile['age'] or '—'}, "
        f"Weight: {profile['weight'] or '—'} kg, "
        f"Height: {profile['height'] or '—'} cm, "
        f"Sex: {sex_label(profile['sex'])}"
    )

    # Small helper: show negative CVD as "−x.x%" correctly
    cvd_pct = stats["cvd_reduction_pct"]

    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>StairLife Tracker</title>
      </head>
      <body style="font-family: system-ui; margin: 40px; max-width: 1100px;">
        <h1 style="margin-bottom: 6px;">StairLife Tracker</h1>
        <p style="margin-top: 0; color:#444;">Step 5: life days + risk model (v0) ✅</p>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top: 18px;">
          <section style="border:1px solid #ddd; border-radius:12px; padding:16px;">
            <h2 style="margin-top:0;">Profile</h2>

            <form method="post" action="/profile">
              <label>Age (years)<br/>
                <input name="age" value="{profile["age"]}" inputmode="numeric"
                       style="width:100%; padding:10px; margin:6px 0 10px;" />
              </label>

              <label>Weight (kg)<br/>
                <input name="weight" value="{profile["weight"]}" inputmode="decimal"
                       style="width:100%; padding:10px; margin:6px 0 10px;" />
              </label>

              <label>Height (cm)<br/>
                <input name="height" value="{profile["height"]}" inputmode="numeric"
                       style="width:100%; padding:10px; margin:6px 0 10px;" />
              </label>

              <label>Sex<br/>
                <select name="sex" style="width:100%; padding:10px; margin:6px 0 10px;">
                  <option value="" {"selected" if profile["sex"] == "" else ""}>— select —</option>
                  <option value="F" {"selected" if profile["sex"] == "F" else ""}>Female</option>
                  <option value="M" {"selected" if profile["sex"] == "M" else ""}>Male</option>
                  <option value="O" {"selected" if profile["sex"] == "O" else ""}>Other / Prefer not to say</option>
                </select>
              </label>

              <button type="submit" style="padding:10px 14px;">Save profile</button>
            </form>

            <div style="margin-top:14px; color:#333;">
              <strong>Current profile:</strong><br/>
              {profile_summary}
            </div>

            <p style="margin-top:12px; color:#666;">
              Stored in <code>stairlife.db</code>.
            </p>
          </section>

          <section style="border:1px solid #ddd; border-radius:12px; padding:16px;">
            <h2 style="margin-top:0;">Add entry</h2>

            <form method="post" action="/entry">
              <label>Date<br/>
                <input type="date" name="entry_date" value="{today_str}"
                       style="width:100%; padding:10px; margin:6px 0 10px;" />
              </label>

              <label>Stair climbs (count)<br/>
                <input name="climbs" value="" inputmode="numeric"
                       style="width:100%; padding:10px; margin:6px 0 10px;" />
              </label>

              <button type="submit" style="padding:10px 14px;">Save entry</button>
            </form>

            <p style="margin-top:12px; color:#666;">
              Re-entering the same date overwrites that day.
            </p>
          </section>
        </div>

        <section style="margin-top: 18px; border:1px solid #ddd; border-radius:12px; padding:16px;">
          <h2 style="margin-top:0;">Stats</h2>

          <div style="display:grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom:10px;">
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">Total climbs</div>
              <div style="font-size:22px; font-weight:700;">{stats["total_climbs"]}</div>
            </div>
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">Tracked days</div>
              <div style="font-size:22px; font-weight:700;">{stats["days_tracked"]}</div>
            </div>
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">Active days</div>
              <div style="font-size:22px; font-weight:700;">{stats["active_days"]}</div>
            </div>
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">Average/day</div>
              <div style="font-size:22px; font-weight:700;">{stats["avg_per_day"]:.2f}</div>
            </div>
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">Consistency</div>
              <div style="font-size:22px; font-weight:700;">{stats["consistency"]:.1f}%</div>
            </div>
          </div>

          <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">Life days gained (est.)</div>
              <div style="font-size:22px; font-weight:700;">{stats["life_days_gained"]:.0f}</div>
              <div style="color:#777; font-size:12px;">Model category: {stats["model_category"]} flights/day</div>
            </div>
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">All-cause mortality risk reduction</div>
              <div style="font-size:22px; font-weight:700;">{stats["all_cause_reduction_pct"]:.1f}%</div>
              <div style="color:#777; font-size:12px;">vs 0 flights/day (v0)</div>
            </div>
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">CVD mortality risk reduction</div>
              <div style="font-size:22px; font-weight:700;">{cvd_pct:.1f}%</div>
              <div style="color:#777; font-size:12px;">negative = no reduction</div>
            </div>
            <div style="border:1px solid #eee; border-radius:12px; padding:12px;">
              <div style="color:#666; font-size:12px;">Average vs max day</div>
              <div style="font-size:22px; font-weight:700;">{stats["avg_vs_max_pct"]:.1f}%</div>
              <div style="color:#777; font-size:12px;">avg/day ÷ max(day)</div>
            </div>
          </div>

          <p style="margin:10px 0 0; color:#666; font-size: 13px;">
            v0 note: This is an observational model (UK Biobank, at-home stair flights/day). We map your Average/day to a category and display the category’s HR/RMST-based estimates.
          </p>
        </section>

        <section style="margin-top: 18px; border:1px solid #ddd; border-radius:12px; padding:16px;">
          <h2 style="margin-top:0;">History</h2>

          <table style="width:100%; border-collapse: collapse;">
            <thead>
              <tr>
                <th style="text-align:left; padding:8px; border-bottom:2px solid #ddd;">Year</th>
                <th style="text-align:left; padding:8px; border-bottom:2px solid #ddd;">Month</th>
                <th style="text-align:left; padding:8px; border-bottom:2px solid #ddd;">Weekday</th>
                <th style="text-align:left; padding:8px; border-bottom:2px solid #ddd;">Date</th>
                <th style="text-align:right; padding:8px; border-bottom:2px solid #ddd;">Climbs</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </section>
      </body>
    </html>
    """


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
