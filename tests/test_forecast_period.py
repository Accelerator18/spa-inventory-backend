from datetime import date

from app.calculations.forecast import build_forecast_period


def test_three_month_horizon_uses_next_full_calendar_months() -> None:
    start, end, days = build_forecast_period(date(2026, 9, 15), None, 3)

    assert start == date(2026, 10, 1)
    assert end == date(2026, 12, 31)
    assert days == 92
