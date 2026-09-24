from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Batch, Location, Movement, MovementAllocation, OpenOrder, Product


PRODUCTS = [
    Product(sku="OIL-001", name="Массажное масло базовое (миндаль)", unit="л", pack_size=5, min_order_qty=10, safety_stock_days=14, lead_time_days=7, default_price=Decimal("1259.05")),
    Product(sku="OIL-002", name="Массажное масло ароматическое (лаванда)", unit="л", pack_size=1, min_order_qty=5, safety_stock_days=14, lead_time_days=7, default_price=Decimal("3223.40")),
    Product(sku="SCRB-020", name="Скраб для тела кофейный", unit="кг", pack_size=1, min_order_qty=5, safety_stock_days=14, lead_time_days=10, default_price=Decimal("1789.50")),
    Product(sku="WRAP-030", name="Альгинатная маска для обёртывания", unit="кг", pack_size=1, min_order_qty=5, safety_stock_days=14, lead_time_days=14, default_price=Decimal("2437.00")),
    Product(sku="FACE-040", name="Крем для лица", unit="л", pack_size=1, min_order_qty=5, safety_stock_days=10, lead_time_days=7, default_price=Decimal("2100.00")),
    Product(sku="TEX-061", name="Халат вафельный", unit="шт", pack_size=10, min_order_qty=20, safety_stock_days=10, lead_time_days=7, default_price=Decimal("1850.00")),
]

LOCATIONS = [
    Location(code="MS-01", name="Красная Поляна"),
    Location(code="MS-02", name="Сочи"),
]


def _receipt(db, *, sku: str, location: str, code: str, qty: float, days_ago: int, expiry_in: int | None, price: float, doc: str) -> Batch:
    today = date.today()
    batch = Batch(
        sku=sku,
        location_code=location,
        code=code,
        expiry_date=today + timedelta(days=expiry_in) if expiry_in is not None else None,
        receipt_unit_price=Decimal(str(price)),
        invoice_no=doc,
    )
    db.add(batch)
    db.flush()
    db.add(Movement(operation_date=today - timedelta(days=days_ago), sku=sku, location_code=location, operation="receipt", qty=qty, batch_id=batch.id, doc_no=doc))
    db.flush()
    return batch


def _seed_consumes(db, *, sku: str, location: str, batches: list[Batch], balances: dict[int, float], weekly: list[float], prefix: str) -> None:
    today = date.today()
    for index, qty in enumerate(weekly):
        if qty <= 0:
            continue
        movement_date = today - timedelta(days=(len(weekly) - 1 - index) * 7)
        movement = Movement(operation_date=movement_date, sku=sku, location_code=location, operation="consume", qty=qty, doc_no=f"{prefix}-{index + 1:02d}")
        db.add(movement)
        db.flush()
        remaining = qty
        eligible = sorted(batches, key=lambda b: (b.expiry_date is None, b.expiry_date or date.max, b.id))
        for batch in eligible:
            available = balances.get(batch.id, 0.0)
            if available <= 0 or remaining <= 1e-9:
                continue
            take = min(available, remaining)
            db.add(MovementAllocation(movement_id=movement.id, batch_id=batch.id, qty=take))
            balances[batch.id] = available - take
            remaining -= take
        if remaining > 1e-6:
            raise RuntimeError(f"Seed stock exhausted for {sku}")


def seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Product.sku).limit(1)) is not None:
            print("Seed already present; skipping")
            return

        db.add_all(PRODUCTS)
        db.add_all(LOCATIONS)
        db.flush()

        oil1 = _receipt(db, sku="OIL-001", location="MS-01", code="B-OIL-001-001", qty=100, days_ago=120, expiry_in=75, price=1195.00, doc="INV-OIL1-001")
        oil2 = _receipt(db, sku="OIL-001", location="MS-01", code="B-OIL-001-002", qty=80, days_ago=70, expiry_in=150, price=1259.05, doc="INV-OIL1-002")
        _seed_consumes(db, sku="OIL-001", location="MS-01", batches=[oil1, oil2], balances={oil1.id: 100.0, oil2.id: 80.0}, weekly=[8.4, 9.1, 8.8, 9.6, 10.2, 9.4, 11.0, 10.6, 12.3, 11.8, 12.9, 13.4], prefix="USE-OIL1")

        scrb = _receipt(db, sku="SCRB-020", location="MS-01", code="B-SCRB-020-001", qty=60, days_ago=100, expiry_in=90, price=1789.50, doc="INV-SCRB-001")
        _seed_consumes(db, sku="SCRB-020", location="MS-01", batches=[scrb], balances={scrb.id: 60.0}, weekly=[3.1, 2.9, 3.4, 3.0, 3.3, 3.2, 3.5, 3.1, 6.8, 7.4, 7.1, 7.6], prefix="USE-SCRB")

        wrap = _receipt(db, sku="WRAP-030", location="MS-02", code="B-WRAP-030-001", qty=105, days_ago=100, expiry_in=120, price=2437.00, doc="INV-WRAP-001")
        _seed_consumes(db, sku="WRAP-030", location="MS-02", batches=[wrap], balances={wrap.id: 105.0}, weekly=[6.2, 5.8, 6.5, 6.0, 0.0, 6.3, 6.1, 6.4, 6.0, 6.6, 6.2, 6.9], prefix="USE-WRAP")

        _receipt(db, sku="FACE-040", location="MS-01", code="B-FACE-040-EXP", qty=20, days_ago=20, expiry_in=9, price=2100.00, doc="INV-FACE-001")
        _receipt(db, sku="TEX-061", location="MS-01", code="B-TEX-061-OLD", qty=40, days_ago=120, expiry_in=None, price=1850.00, doc="INV-TEX-001")
        oil2_batch = _receipt(db, sku="OIL-002", location="MS-02", code="B-OIL-002-001", qty=20, days_ago=45, expiry_in=160, price=3223.40, doc="INV-OIL2-001")
        _seed_consumes(db, sku="OIL-002", location="MS-02", batches=[oil2_batch], balances={oil2_batch.id: 20.0}, weekly=[1.0, 1.2, 1.1, 1.4], prefix="USE-OIL2")

        db.add_all([
            OpenOrder(sku="OIL-001", location_code="MS-01", qty=20, expected_delivery_date=date.today() + timedelta(days=5), status="confirmed", unit_price=Decimal("1275.00")),
            OpenOrder(sku="WRAP-030", location_code="MS-02", qty=30, expected_delivery_date=date.today() + timedelta(days=12), status="delayed", unit_price=Decimal("2500.00")),
        ])
        db.commit()
        print("Seed loaded")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
