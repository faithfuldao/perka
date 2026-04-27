"""apple wallet web service support

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add authentication_token to passes (nullable first, backfill, then non-null)
    op.add_column('passes', sa.Column('authentication_token', sa.String(64), nullable=True))
    op.execute("UPDATE passes SET authentication_token = replace(gen_random_uuid()::text, '-', '') WHERE authentication_token IS NULL")
    op.alter_column('passes', 'authentication_token', nullable=False)

    # Create device registrations table
    op.create_table(
        'apple_device_registrations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('device_library_identifier', sa.String(200), nullable=False),
        sa.Column('push_token', sa.String(200), nullable=False),
        sa.Column('pass_serial_number', sa.String(36), nullable=False),
        sa.Column('pass_type_identifier', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pass_serial_number'], ['passes.serial_number'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_library_identifier', 'pass_serial_number', name='uq_device_pass'),
    )
    op.create_index('ix_apple_device_registrations_serial', 'apple_device_registrations', ['pass_serial_number'])


def downgrade() -> None:
    op.drop_index('ix_apple_device_registrations_serial', table_name='apple_device_registrations')
    op.drop_table('apple_device_registrations')
    op.drop_column('passes', 'authentication_token')
