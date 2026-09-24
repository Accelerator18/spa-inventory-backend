from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.stock import StockDetailOut, StockItem
from app.services.stock import get_stock_detail, list_stock

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("", response_model=list[StockItem])
def get_stock(
    sku: str | None = None,
    location: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    return list_stock(db, sku=sku, location=location)


@router.get("/{sku}", response_model=StockDetailOut)
def get_stock_by_sku(sku: str, db: Session = Depends(get_db)) -> dict:
    return get_stock_detail(db, sku)
