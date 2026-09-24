from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class MovementOperation(StrEnum):
    RECEIPT = "receipt"
    CONSUME = "consume"
    WRITEOFF = "writeoff"
    RETURN = "return"
    CORRECTION = "correction"


class MovementCreate(BaseModel):
    date: date
    sku: str = Field(min_length=1, max_length=32)
    location: str = Field(min_length=1, max_length=32)
    operation: MovementOperation
    qty: float
    batch: str | None = Field(default=None, max_length=64)
    doc_no: str = Field(min_length=1, max_length=64)


class AllocationOut(BaseModel):
    batch: str
    qty: float


class MovementOut(BaseModel):
    id: int
    date: date
    sku: str
    location: str
    operation: str
    qty: float
    batch: str | None
    doc_no: str
    allocations: list[AllocationOut] = Field(default_factory=list)


class MovementCreatedOut(MovementOut):
    current_stock: float


class MovementListOut(BaseModel):
    items: list[MovementOut]
    total: int
    limit: int
    offset: int
