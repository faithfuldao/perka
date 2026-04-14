"""brand google wallet design fields

Revision ID: a1b2c3d4e5f6
Revises: 759261d50fb5
Create Date: 2026-04-14 19:30:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '759261d50fb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('brands', sa.Column('google_hero_image_url', sa.String(length=500), nullable=True))
    op.add_column('brands', sa.Column('google_stamp_image_url', sa.String(length=500), nullable=True))
    op.add_column('brands', sa.Column('google_card_title', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('brands', 'google_card_title')
    op.drop_column('brands', 'google_stamp_image_url')
    op.drop_column('brands', 'google_hero_image_url')
