"""add owner_id to meetings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-22 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('meetings', sa.Column('owner_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_meetings_owner_id'), 'meetings', ['owner_id'], unique=False)
    op.create_foreign_key(
        'fk_meetings_owner_id_users', 'meetings', 'users',
        ['owner_id'], ['id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_meetings_owner_id_users', 'meetings', type_='foreignkey')
    op.drop_index(op.f('ix_meetings_owner_id'), table_name='meetings')
    op.drop_column('meetings', 'owner_id')