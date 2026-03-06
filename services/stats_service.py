from services.health_model import estimate_from_avg


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
