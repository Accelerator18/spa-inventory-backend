from datetime import date, timedelta

import pytest

from app.calculations.inventory import (
    BatchBalance,
    allocate_fefo,
    calculate_reorder_point,
    calculate_stock_balance,
    raw_recommended_qty,
    round_recommended_qty,
)
from app.exceptions import InsufficientStockError


def test_fefo_uses_nearest_expiry_first() -> None:
    today = date(2026, 9, 24)
    batches = [
        BatchBalance(1, "B-LATE", 10.0, today + timedelta(days=30)),
        BatchBalance(2, "B-SOON", 3.0, today + timedelta(days=5)),
    ]

    allocations = allocate_fefo(batches, 5.0, today)

    assert [(item.batch_code, item.qty) for item in allocations] == [
        ("B-SOON", 3.0),
        ("B-LATE", 2.0),
    ]


def test_fefo_skips_expired_batch() -> None:
    today = date(2026, 9, 24)
    batches = [
        BatchBalance(1, "EXPIRED", 100.0, today - timedelta(days=1)),
        BatchBalance(2, "VALID", 10.0, today + timedelta(days=5)),
    ]

    allocations = allocate_fefo(batches, 4.0, today)

    assert len(allocations) == 1
    assert allocations[0].batch_code == "VALID"
    assert allocations[0].qty == 4.0


def test_fefo_rejects_consumption_above_available_stock() -> None:
    today = date(2026, 9, 24)
    batches = [BatchBalance(1, "B1", 2.5, today + timedelta(days=10))]

    with pytest.raises(InsufficientStockError) as exc_info:
        allocate_fefo(batches, 3.0, today)

    assert exc_info.value.available_qty == 2.5


def test_stock_is_reconstructed_from_movements() -> None:
    movements = [
        ("receipt", 20.0),
        ("consume", 6.0),
        ("return", 2.0),
        ("writeoff", 1.0),
        ("correction", -0.5),
    ]

    assert calculate_stock_balance(movements) == 14.5


def test_purchase_qty_is_rounded_to_pack_and_minimum_order() -> None:
    assert round_recommended_qty(73.98, pack_size=5.0, min_order_qty=10.0) == 75.0
    assert round_recommended_qty(3.0, pack_size=5.0, min_order_qty=10.0) == 10.0


def test_reorder_point_includes_lead_time_and_safety_stock() -> None:
    result = calculate_reorder_point(avg_daily=1.362, lead_time_days=7, safety_stock_days=14)
    assert result == 28.602


def test_zero_recommendation_when_stock_and_incoming_cover_need() -> None:
    raw = raw_recommended_qty(
        forecast_demand=30.0,
        safety_stock=10.0,
        current_stock=25.0,
        incoming_qty=20.0,
    )
    assert raw == 0.0
    assert round_recommended_qty(raw, pack_size=5.0, min_order_qty=10.0) == 0.0
