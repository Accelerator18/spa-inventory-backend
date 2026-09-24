from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculations.inventory import average_daily_consumption, calculate_stock_days
from app.config import settings
from app.models import Movement, Product
from app.services.inventory import get_batch_balances, get_consumption_total, get_last_movement_date, get_total_stock


def get_alerts(
    db: Session,
    *,
    location: str | None = None,
    alert_type: str | None = None,
    severity: str | None = None,
) -> list[dict]:
    stmt = select(Movement.sku, Movement.location_code).distinct()
    if location:
        stmt = stmt.where(Movement.location_code == location)
    pairs = db.execute(stmt).all()

    today = date.today()
    alerts: list[dict] = []
    for sku, loc in pairs:
        product = db.get(Product, sku)
        current = get_total_stock(db, sku, loc)
        avg = average_daily_consumption(get_consumption_total(db, sku, loc, today), 90)
        days_left = calculate_stock_days(current, avg)

        if days_left is not None and days_left < product.lead_time_days:
            sev = "critical" if days_left < product.lead_time_days / 2 else "high"
            alerts.append(
                {
                    "type": "deficit_risk",
                    "severity": sev,
                    "sku": sku,
                    "location": loc,
                    "message": "Stock coverage is shorter than supplier lead time",
                    "metrics": {
                        "current_stock": current,
                        "avg_daily_consumption": avg,
                        "stock_days": days_left,
                        "lead_time_days": product.lead_time_days,
                    },
                }
            )

        for batch in get_batch_balances(db, sku, loc):
            if batch.qty <= 0 or batch.expiry_date is None or batch.expiry_date < today:
                continue
            days_to_expiry = (batch.expiry_date - today).days
            if days_to_expiry <= settings.expiry_alert_days:
                sev = "critical" if days_to_expiry <= 7 else "high"
                alerts.append(
                    {
                        "type": "expiry_risk",
                        "severity": sev,
                        "sku": sku,
                        "location": loc,
                        "message": f"Batch {batch.batch_code} expires soon",
                        "metrics": {
                            "batch": batch.batch_code,
                            "qty": batch.qty,
                            "expiry_date": batch.expiry_date.isoformat(),
                            "days_to_expiry": days_to_expiry,
                        },
                    }
                )

        last_date = get_last_movement_date(db, sku, loc)
        days_without_movement = (today - last_date).days if last_date else None
        if last_date is None or days_without_movement >= settings.no_movement_days:
            alerts.append(
                {
                    "type": "no_movement",
                    "severity": "info",
                    "sku": sku,
                    "location": loc,
                    "message": "No stock movements for the configured threshold period",
                    "metrics": {
                        "last_movement_date": last_date.isoformat() if last_date else None,
                        "days_without_movement": days_without_movement,
                        "threshold_days": settings.no_movement_days,
                        "current_stock": current,
                    },
                }
            )

    if alert_type:
        alerts = [item for item in alerts if item["type"] == alert_type]
    if severity:
        alerts = [item for item in alerts if item["severity"] == severity]
    severity_rank = {"critical": 0, "high": 1, "warning": 2, "info": 3}
    alerts.sort(key=lambda item: (severity_rank.get(item["severity"], 9), item["sku"], item["location"]))
    return alerts
