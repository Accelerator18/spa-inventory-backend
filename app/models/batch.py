from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint("sku", "location_code", "code", name="uq_batch_sku_location_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku", ondelete="RESTRICT"), nullable=False)
    location_code: Mapped[str] = mapped_column(ForeignKey("locations.code", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    receipt_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    invoice_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
