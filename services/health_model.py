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
