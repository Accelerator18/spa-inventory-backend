import calendar
from datetime import date, timedelta
from math import ceil


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def build_forecast_period(
    as_of: date,
    horizon_days: int | None,
    horizon_months: int | None,
) -> tuple[date, date, int]:
    """Build period. Month horizon means the next N full calendar months."""
    if horizon_days is not None:
        start = as_of
        end = as_of + timedelta(days=horizon_days - 1)
        return start, end, horizon_days

    if horizon_months is None:
        raise ValueError("A horizon is required")

    start_year, start_month = _add_months(as_of.year, as_of.month, 1)
    start = date(start_year, start_month, 1)
    end_year, end_month = _add_months(start_year, start_month, horizon_months - 1)
    end = date(end_year, end_month, calendar.monthrange(end_year, end_month)[1])
    return start, end, (end - start).days + 1


def estimate_stockout_date(
    as_of: date,
    current_stock: float,
    avg_daily: float,
    incoming: list[tuple[date, float]],
) -> date | None:
    """Estimate stockout while adding only supplies that arrive before depletion."""
    if avg_daily <= 0:
        return None
    remaining = max(current_stock, 0.0)
    cursor = as_of

    for delivery_date, qty in sorted(incoming, key=lambda item: item[0]):
        if delivery_date < cursor:
            remaining += max(qty, 0.0)
            continue
        days_until_delivery = (delivery_date - cursor).days
        demand_until_delivery = avg_daily * days_until_delivery
        if remaining <= demand_until_delivery + 1e-9:
            return cursor + timedelta(days=ceil(remaining / avg_daily))
        remaining -= demand_until_delivery
        remaining += max(qty, 0.0)
        cursor = delivery_date

    return cursor + timedelta(days=ceil(remaining / avg_daily))
