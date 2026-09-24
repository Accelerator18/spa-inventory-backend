from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculations.inventory import average_daily_consumption, calculate_stock_days
from app.exceptions import NotFoundError
from app.models import Batch, Location, Movement, Product
from app.services.inventory import get_batch_balances, get_consumption_total, get_total_stock


def list_stock(db: Session, sku: str | None = None, location: str | None = None) -> list[dict]:
    stmt = select(Movement.sku, Movement.location_code).distinct()
    if sku:
        stmt = stmt.where(Movement.sku == sku)
    if location:
        stmt = stmt.where(Movement.location_code == location)
    pairs = db.execute(stmt).all()

    result: list[dict] = []
    today = date.today()
    for item_sku, item_location in pairs:
        product = db.get(Product, item_sku)
        current = get_total_stock(db, item_sku, item_location)
        avg = average_daily_consumption(get_consumption_total(db, item_sku, item_location, today), 90)
        balances = get_batch_balances(db, item_sku, item_location)
        expiry_dates = [b.expiry_date for b in balances if b.qty > 0 and b.expiry_date and b.expiry_date >= today]
        result.append(
            {
                "sku": item_sku,
                "name": product.name,
                "unit": product.unit,
                "location": item_location,
                "current_stock": current,
                "avg_daily_consumption": avg,
                "stock_days": calculate_stock_days(current, avg),
                "nearest_expiry": min(expiry_dates) if expiry_dates else None,
            }
        )
    return result


def get_stock_detail(db: Session, sku: str) -> dict:
    product = db.get(Product, sku)
    if product is None:
        raise NotFoundError(f"Unknown SKU: {sku}")

    locations = db.scalars(
        select(Location).join(Movement, Movement.location_code == Location.code).where(Movement.sku == sku).distinct()
    ).all()
    today = date.today()
    location_rows: list[dict] = []
    for location in locations:
        current = get_total_stock(db, sku, location.code)
        avg = average_daily_consumption(get_consumption_total(db, sku, location.code, today), 90)
        balances = {item.batch_id: item for item in get_batch_balances(db, sku, location.code)}
        batches = db.scalars(
            select(Batch).where(Batch.sku == sku, Batch.location_code == location.code).order_by(Batch.expiry_date.asc().nulls_last())
        ).all()
        batch_rows = []
        for batch in batches:
            qty = balances[batch.id].qty
            if qty <= 0:
                continue
            batch_rows.append(
                {
                    "batch": batch.code,
                    "qty": qty,
                    "expiry_date": batch.expiry_date,
                    "unit_price": float(batch.receipt_unit_price) if batch.receipt_unit_price is not None else None,
                    "invoice_no": batch.invoice_no,
                }
            )
        location_rows.append(
            {
                "location": location.code,
                "current_stock": current,
                "avg_daily_consumption": avg,
                "stock_days": calculate_stock_days(current, avg),
                "batches": batch_rows,
            }
        )

    return {"sku": sku, "name": product.name, "unit": product.unit, "locations": location_rows}
