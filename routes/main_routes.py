from datetime import date

from flask import Blueprint, Response, redirect, render_template, request, url_for

from models.database import (
    load_entries,
    load_profile,
    remove_entry,
    update_profile,
    upsert_entry,
)

from services.stats_service import compute_stats
from services.trends_service import add_bar_widths, monthly_summary, weekly_summary


main_bp = Blueprint("main", __name__)


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sex_label(code: str) -> str:
    return {"F": "Female", "M": "Male", "O": "Other / Prefer not to say"}.get(code, "—")


@main_bp.get("/")
def index():
    profile = load_profile()
    entries_sorted = load_entries()
    stats = compute_stats(entries_sorted)

    weekly = add_bar_widths(weekly_summary(entries_sorted, weeks=8))
    monthly = add_bar_widths(monthly_summary(entries_sorted, months=12))

    profile_summary = (
        f"Age: {profile['age'] or '—'}, "
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


@main_bp.post("/profile")
def save_profile():
    age = (request.form.get("age") or "").strip()
    weight = (request.form.get("weight") or "").strip()
    height = (request.form.get("height") or "").strip()
    sex = (request.form.get("sex") or "").strip()

    update_profile(age, weight, height, sex)

    return redirect(url_for("main.index"))


@main_bp.post("/entry")
def save_entry():
    entry_date = (request.form.get("entry_date") or "").strip()
    climbs = safe_int((request.form.get("climbs") or "").strip(), default=0)

    if climbs < 0:
        climbs = 0

    if entry_date:
        upsert_entry(entry_date, climbs)

    return redirect(url_for("main.index"))


@main_bp.post("/entry/delete")
def delete_entry():
    entry_date = (request.form.get("entry_date") or "").strip()

    if entry_date:
        remove_entry(entry_date)

    return redirect(url_for("main.index"))


@main_bp.get("/export.csv")
def export_csv():
    entries = load_entries()
    lines = ["date,year,month,weekday,climbs"]

    for e in entries:
        lines.append(f'{e["date"]},{e["year"]},{e["month"]},{e["weekday"]},{e["climbs"]}')

    csv_text = "\n".join(lines) + "\n"

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=stairlife_export.csv"},
    )
