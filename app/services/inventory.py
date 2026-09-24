from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.calculations.inventory import BatchBalance, calculate_stock_days, stock_delta
from app.models import Batch, Movement, MovementAllocation, OpenOrder


def get_total_stock(db: Session, sku: str, location: str) -> float:
    rows = db.execute(
        select(Movement.operation, Movement.qty).where(
            Movement.sku == sku,
            Movement.location_code == location,
        )
    ).all()
    return round(sum(stock_delta(operation, float(qty)) for operation, qty in rows), 3)


def get_batch_balances(db: Session, sku: str, location: str, as_of: date | None = None) -> list[BatchBalance]:
    batches = db.scalars(
        select(Batch)
        .where(Batch.sku == sku, Batch.location_code == location)
        .order_by(Batch.expiry_date.asc().nulls_last(), Batch.id.asc())
    ).all()

    result: list[BatchBalance] = []
    for batch in batches:
        movement_stmt = select(Movement.operation, Movement.qty).where(Movement.batch_id == batch.id)
        if as_of is not None:
            movement_stmt = movement_stmt.where(Movement.operation_date <= as_of)
        movement_rows = db.execute(movement_stmt).all()
        movement_balance = sum(stock_delta(operation, float(qty)) for operation, qty in movement_rows)

        allocation_stmt = (
            select(func.coalesce(func.sum(MovementAllocation.qty), 0))
            .join(Movement, Movement.id == MovementAllocation.movement_id)
            .where(MovementAllocation.batch_id == batch.id)
        )
        if as_of is not None:
            allocation_stmt = allocation_stmt.where(Movement.operation_date <= as_of)
        allocated = db.scalar(allocation_stmt)
        qty = round(movement_balance - float(allocated or 0), 3)
        result.append(BatchBalance(batch.id, batch.code, qty, batch.expiry_date))
    return result


def get_consumption_total(db: Session, sku: str, location: str, as_of: date, days: int = 90) -> float:
    start_date = as_of - timedelta(days=days - 1)
    total = db.scalar(
        select(func.coalesce(func.sum(Movement.qty), 0)).where(
            Movement.sku == sku,
            Movement.location_code == location,
            Movement.operation == "consume",
            Movement.operation_date >= start_date,
            Movement.operation_date <= as_of,
        )
    )
    return float(total or 0)


def get_last_movement_date(db: Session, sku: str, location: str) -> date | None:
    return db.scalar(
        select(func.max(Movement.operation_date)).where(
            Movement.sku == sku,
            Movement.location_code == location,
        )
    )


def get_latest_unit_price(db: Session, sku: str, location: str) -> float | None:
    price = db.scalar(
        select(Batch.receipt_unit_price)
        .where(
            Batch.sku == sku,
            Batch.location_code == location,
            Batch.receipt_unit_price.is_not(None),
        )
        .order_by(Batch.id.desc())
        .limit(1)
    )
    return float(price) if price is not None else None


def get_incoming_orders(
    db: Session,
    sku: str,
    location: str,
    from_date: date,
    to_date: date | None = None,
) -> list[OpenOrder]:
    stmt = select(OpenOrder).where(
        OpenOrder.sku == sku,
        OpenOrder.location_code == location,
        OpenOrder.status.in_(["ordered", "confirmed", "delayed"]),
        OpenOrder.expected_delivery_date >= from_date,
    )
    if to_date is not None:
        stmt = stmt.where(OpenOrder.expected_delivery_date <= to_date)
    return list(db.scalars(stmt.order_by(OpenOrder.expected_delivery_date.asc())).all())


def stock_days(current_stock: float, avg_daily: float) -> float | None:
    return calculate_stock_days(current_stock, avg_daily)
