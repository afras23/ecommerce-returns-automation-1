"""return_record_observability_fields

Revision ID: 16c106781b6b
Revises: 4ec055860c16
Create Date: 2026-03-31 00:44:08.510905

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "16c106781b6b"
down_revision: Union[str, None] = "4ec055860c16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("returns", sa.Column("product_id", sa.String(), nullable=True))
    op.add_column("returns", sa.Column("customer_segment", sa.String(), nullable=True))
    op.add_column("returns", sa.Column("fraud_score", sa.Float(), nullable=True))
    op.add_column("returns", sa.Column("processing_time_ms", sa.Float(), nullable=True))
    op.add_column("returns", sa.Column("shipping_label_json", sa.Text(), nullable=True))
    op.create_index(op.f("ix_returns_product_id"), "returns", ["product_id"], unique=False)
    op.create_index(op.f("ix_returns_customer_segment"), "returns", ["customer_segment"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_returns_customer_segment"), table_name="returns")
    op.drop_index(op.f("ix_returns_product_id"), table_name="returns")
    op.drop_column("returns", "shipping_label_json")
    op.drop_column("returns", "processing_time_ms")
    op.drop_column("returns", "fraud_score")
    op.drop_column("returns", "customer_segment")
    op.drop_column("returns", "product_id")
