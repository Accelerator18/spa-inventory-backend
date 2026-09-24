from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OpenOrder(Base):
    __tablename__ = "open_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(ForeignKey("products.sku", ondelete="RESTRICT"), nullable=False)
    location_code: Mapped[str] = mapped_column(ForeignKey("locations.code", ondelete="RESTRICT"), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    expected_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
