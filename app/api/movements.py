from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.movement import MovementCreate, MovementCreatedOut, MovementListOut, MovementOut
from app.services.movements import create_movement, list_movements

router = APIRouter(prefix="/api/movements", tags=["movements"])


def _serialize(movement) -> dict:
    return {
        "id": movement.id,
        "date": movement.operation_date,
        "sku": movement.sku,
        "location": movement.location_code,
        "operation": movement.operation,
        "qty": float(movement.qty),
        "batch": movement.batch.code if movement.batch is not None else None,
        "doc_no": movement.doc_no,
        "allocations": [
            {"batch": allocation.batch.code, "qty": float(allocation.qty)}
            for allocation in movement.allocations
        ],
    }


@router.post("", response_model=MovementCreatedOut, status_code=201)
def post_movement(payload: MovementCreate, db: Session = Depends(get_db)) -> dict:
    movement, current_stock = create_movement(db, payload)
    data = _serialize(movement)
    data["current_stock"] = current_stock
    return data


@router.get("", response_model=MovementListOut)
def get_movements(
    sku: str | None = None,
    location: str | None = None,
    operation: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    items, total = list_movements(
        db,
        sku=sku,
        location=location,
        operation=operation,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [_serialize(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
