from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.calculations.inventory import allocate_fefo
from app.exceptions import BadRequestError, ConflictError, InsufficientStockError, NotFoundError, ValidationError
from app.models import Batch, Location, Movement, MovementAllocation, Product
from app.schemas.movement import MovementCreate
from app.services.inventory import get_batch_balances, get_total_stock


def _require_product_location(db: Session, sku: str, location: str) -> tuple[Product, Location]:
    product = db.get(Product, sku)
    if product is None:
        raise NotFoundError(f"Unknown SKU: {sku}")
    location_obj = db.get(Location, location)
    if location_obj is None:
        raise NotFoundError(f"Unknown location: {location}")
    return product, location_obj


def _validate_qty(operation: str, qty: float) -> None:
    if operation in {"receipt", "consume", "return", "writeoff"} and qty <= 0:
        raise ValidationError(f"qty must be greater than zero for {operation}")
    if operation == "correction" and qty == 0:
        raise ValidationError("qty must be non-zero for correction")


def _find_batch(db: Session, sku: str, location: str, code: str) -> Batch | None:
    return db.scalar(
        select(Batch).where(
            Batch.sku == sku,
            Batch.location_code == location,
            Batch.code == code,
        )
    )


def create_movement(db: Session, payload: MovementCreate) -> tuple[Movement, float]:
    product, _ = _require_product_location(db, payload.sku, payload.location)
    operation = payload.operation.value

    if payload.date > date.today():
        raise ValidationError("Operation date cannot be in the future")
    _validate_qty(operation, payload.qty)

    duplicate = db.scalar(select(Movement.id).where(Movement.doc_no == payload.doc_no))
    if duplicate is not None:
        raise ConflictError(f"Document {payload.doc_no} already exists")

    movement = Movement(
        operation_date=payload.date,
        sku=payload.sku,
        location_code=payload.location,
        operation=operation,
        qty=payload.qty,
        doc_no=payload.doc_no,
    )

    if operation == "consume":
        balances = get_batch_balances(db, payload.sku, payload.location, as_of=payload.date)
        allocations = allocate_fefo(balances, payload.qty, payload.date)
        db.add(movement)
        db.flush()
        for allocation in allocations:
            db.add(
                MovementAllocation(
                    movement_id=movement.id,
                    batch_id=allocation.batch_id,
                    qty=allocation.qty,
                )
            )
    else:
        if not payload.batch:
            raise ValidationError(f"batch is required for {operation}")
        batch = _find_batch(db, payload.sku, payload.location, payload.batch)
        if batch is None:
            if operation != "receipt":
                raise ValidationError(f"Unknown batch: {payload.batch}")
            batch = Batch(
                sku=payload.sku,
                location_code=payload.location,
                code=payload.batch,
                expiry_date=None,
                receipt_unit_price=product.default_price,
                invoice_no=payload.doc_no,
            )
            db.add(batch)
            db.flush()

        if operation in {"writeoff", "correction"} and (operation == "writeoff" or payload.qty < 0):
            balance = next((item.qty for item in get_batch_balances(db, payload.sku, payload.location) if item.batch_id == batch.id), 0.0)
            requested = payload.qty if operation == "writeoff" else abs(payload.qty)
            if requested > balance + 1e-9:
                raise InsufficientStockError(requested, balance)

        movement.batch_id = batch.id
        db.add(movement)

    db.commit()
    db.refresh(movement)
    current_stock = get_total_stock(db, payload.sku, payload.location)
    return movement, current_stock


def list_movements(
    db: Session,
    *,
    sku: str | None,
    location: str | None,
    operation: str | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> tuple[list[Movement], int]:
    if date_from and date_to and date_from > date_to:
        raise BadRequestError("date_from cannot be later than date_to")

    conditions = []
    if sku:
        conditions.append(Movement.sku == sku)
    if location:
        conditions.append(Movement.location_code == location)
    if operation:
        conditions.append(Movement.operation == operation)
    if date_from:
        conditions.append(Movement.operation_date >= date_from)
    if date_to:
        conditions.append(Movement.operation_date <= date_to)

    total = int(db.scalar(select(func.count()).select_from(Movement).where(*conditions)) or 0)
    rows = db.scalars(
        select(Movement)
        .options(selectinload(Movement.allocations))
        .where(*conditions)
        .order_by(Movement.operation_date.desc(), Movement.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(rows), total
