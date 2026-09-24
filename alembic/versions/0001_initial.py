"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("sku", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("pack_size", sa.Numeric(14, 3), nullable=False),
        sa.Column("min_order_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("safety_stock_days", sa.Integer(), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("default_price", sa.Numeric(14, 2), nullable=False),
    )

    op.create_table(
        "locations",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sku", sa.String(32), sa.ForeignKey("products.sku", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_code", sa.String(32), sa.ForeignKey("locations.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("receipt_unit_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("invoice_no", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("sku", "location_code", "code", name="uq_batch_sku_location_code"),
    )
    op.create_index("ix_batches_sku_location", "batches", ["sku", "location_code"])

    op.create_table(
        "movements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(32), sa.ForeignKey("products.sku", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_code", sa.String(32), sa.ForeignKey("locations.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("doc_no", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_movements_sku_location_date", "movements", ["sku", "location_code", "operation_date"])
    op.create_index("ix_movements_operation", "movements", ["operation"])

    op.create_table(
        "movement_allocations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("movement_id", sa.Integer(), sa.ForeignKey("movements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.UniqueConstraint("movement_id", "batch_id", name="uq_movement_allocation_batch"),
    )

    op.create_table(
        "open_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sku", sa.String(32), sa.ForeignKey("products.sku", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_code", sa.String(32), sa.ForeignKey("locations.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("expected_delivery_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=True),
    )
    op.create_index("ix_open_orders_sku_location", "open_orders", ["sku", "location_code"])


def downgrade() -> None:
    op.drop_index("ix_open_orders_sku_location", table_name="open_orders")
    op.drop_table("open_orders")
    op.drop_table("movement_allocations")
    op.drop_index("ix_movements_operation", table_name="movements")
    op.drop_index("ix_movements_sku_location_date", table_name="movements")
    op.drop_table("movements")
    op.drop_index("ix_batches_sku_location", table_name="batches")
    op.drop_table("batches")
    op.drop_table("locations")
    op.drop_table("products")
