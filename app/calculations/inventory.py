from dataclasses import dataclass
from datetime import date
from math import isfinite

from app.exceptions import InsufficientStockError


@dataclass(frozen=True)
class BatchBalance:
    batch_id: int
    batch_code: str
    qty: float
    expiry_date: date | None


@dataclass(frozen=True)
class Allocation:
    batch_id: int
    batch_code: str
    qty: float


def stock_delta(operation: str, qty: float) -> float:
    """Return signed stock delta for a movement operation."""
    if operation in {"receipt", "return"}:
        return qty
    if operation in {"consume", "writeoff"}:
        return -qty
    if operation == "correction":
        return qty
    raise ValueError(f"Unsupported operation: {operation}")


def calculate_stock_balance(movements: list[tuple[str, float]]) -> float:
    """Calculate current stock only from movement history."""
    return round(sum(stock_delta(operation, qty) for operation, qty in movements), 3)


def allocate_fefo(
    batches: list[BatchBalance],
    requested_qty: float,
    as_of: date,
) -> list[Allocation]:
    """Allocate consumption by FEFO, excluding expired batches."""
    if requested_qty <= 0:
        raise ValueError("requested_qty must be positive")

    eligible = [
        batch
        for batch in batches
        if batch.qty > 0 and (batch.expiry_date is None or batch.expiry_date >= as_of)
    ]
    eligible.sort(key=lambda batch: (batch.expiry_date is None, batch.expiry_date or date.max, batch.batch_id))

    available = sum(batch.qty for batch in eligible)
    if available + 1e-9 < requested_qty:
        raise InsufficientStockError(requested_qty, available)

    remaining = requested_qty
    allocations: list[Allocation] = []
    for batch in eligible:
        if remaining <= 1e-9:
            break
        take = min(batch.qty, remaining)
        allocations.append(Allocation(batch.batch_id, batch.batch_code, round(take, 3)))
        remaining -= take

    return allocations


def average_daily_consumption(total_consumption: float, window_days: int = 90) -> float:
    if window_days <= 0:
        raise ValueError("window_days must be positive")
    return round(max(total_consumption, 0.0) / window_days, 3)


def calculate_safety_stock(avg_daily: float, safety_stock_days: int) -> float:
    return round(max(avg_daily, 0.0) * max(safety_stock_days, 0), 3)


def calculate_reorder_point(avg_daily: float, lead_time_days: int, safety_stock_days: int) -> float:
    safety = calculate_safety_stock(avg_daily, safety_stock_days)
    return round(max(avg_daily, 0.0) * max(lead_time_days, 0) + safety, 3)


def raw_recommended_qty(
    forecast_demand: float,
    safety_stock: float,
    current_stock: float,
    incoming_qty: float,
) -> float:
    return max(0.0, forecast_demand + safety_stock - current_stock - incoming_qty)


def round_recommended_qty(required_qty: float, pack_size: float, min_order_qty: float) -> float:
    """Round upward to both package size and supplier minimum order."""
    if required_qty <= 0:
        return 0.0
    if pack_size <= 0 or min_order_qty < 0:
        raise ValueError("Invalid pack/min-order parameters")

    target = max(required_qty, min_order_qty)
    packs = int(-(-target // pack_size))
    result = packs * pack_size
    if result + 1e-9 < min_order_qty:
        packs = int(-(-min_order_qty // pack_size))
        result = packs * pack_size
    if not isfinite(result):
        raise ValueError("Non-finite purchase quantity")
    return round(result, 3)


def calculate_estimated_cost(qty: float, unit_price: float) -> float:
    return round(max(qty, 0.0) * max(unit_price, 0.0), 2)


def calculate_stock_days(current_stock: float, avg_daily: float) -> float | None:
    if avg_daily <= 0:
        return None
    return round(max(current_stock, 0.0) / avg_daily, 1)
