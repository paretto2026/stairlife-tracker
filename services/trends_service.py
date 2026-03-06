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
            "total": buckets[(y, w)],
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
            "total": buckets[(y, m)],
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
