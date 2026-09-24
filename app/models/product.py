from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    pack_size: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    min_order_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    safety_stock_days: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    default_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
