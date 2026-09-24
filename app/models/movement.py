from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Movement(Base):
    __tablename__ = "movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku", ondelete="RESTRICT"), nullable=False)
    location_code: Mapped[str] = mapped_column(ForeignKey("locations.code", ondelete="RESTRICT"), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id", ondelete="RESTRICT"), nullable=True)
    doc_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    batch = relationship("Batch", lazy="joined")
    allocations = relationship("MovementAllocation", back_populates="movement", cascade="all, delete-orphan", lazy="selectin")


class MovementAllocation(Base):
    __tablename__ = "movement_allocations"
    __table_args__ = (
        UniqueConstraint("movement_id", "batch_id", name="uq_movement_allocation_batch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movement_id: Mapped[int] = mapped_column(ForeignKey("movements.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)

    movement = relationship("Movement", back_populates="allocations")
    batch = relationship("Batch", lazy="joined")
