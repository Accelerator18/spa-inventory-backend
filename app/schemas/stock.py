from datetime import date

from pydantic import BaseModel


class StockItem(BaseModel):
    sku: str
    name: str
    unit: str
    location: str
    current_stock: float
    avg_daily_consumption: float
    stock_days: float | None
    nearest_expiry: date | None


class BatchStockOut(BaseModel):
    batch: str
    qty: float
    expiry_date: date | None
    unit_price: float | None
    invoice_no: str | None


class LocationStockDetail(BaseModel):
    location: str
    current_stock: float
    avg_daily_consumption: float
    stock_days: float | None
    batches: list[BatchStockOut]


class StockDetailOut(BaseModel):
    sku: str
    name: str
    unit: str
    locations: list[LocationStockDetail]
