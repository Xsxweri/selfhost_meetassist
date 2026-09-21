"""add transcripts table for hybrid design

Revision ID: 2c5ed3cd2d1c
Revises: 486be889930e
Create Date: 2026-09-21 19:37:52.554284

"""
from typing import Sequence, Union
import pgvector.sqlalchemy
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2c5ed3cd2d1c'
down_revision: Union[str, Sequence[str], None] = '486be889930e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'transcripts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('meeting_id', sa.UUID(), nullable=False),
        sa.Column('segments', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='带时间戳的ASR分段JSON'),
        sa.Column('text', sa.Text(), nullable=True, comment='分段纯文本'),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=True, comment='文本向量(bge-m3)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_transcripts_meeting_id'), 'transcripts', ['meeting_id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_transcripts_meeting_id'), table_name='transcripts')
    op.drop_table('transcripts')
