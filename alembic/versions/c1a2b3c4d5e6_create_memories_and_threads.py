"""
建memories和conversation_threads表

Revision ID: c1a2b3c4d5e6
Revises: f6a7b8c9d0e1
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

import pgvector.sqlalchemy
from alembic import op
import sqlalchemy as sa


revision: str = 'c1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        'memories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('meeting_id', sa.UUID(), nullable=True),
        sa.Column('source_transcript_id', sa.UUID(), nullable=True),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=True),
        sa.Column('importance', sa.Float(), server_default=sa.text('0.5'), nullable=False),
        sa.Column('confidence', sa.Float(), server_default=sa.text('1.0'), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by', sa.UUID(), nullable=True),
        sa.Column('access_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['superseded_by'], ['memories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memories_owner_id'), 'memories', ['owner_id'], unique=False)
    op.create_index(op.f('ix_memories_kind'), 'memories', ['kind'], unique=False)
    op.create_index(op.f('ix_memories_subject'), 'memories', ['subject'], unique=False)
    op.create_index(op.f('ix_memories_meeting_id'), 'memories', ['meeting_id'], unique=False)
    op.create_index(op.f('ix_memories_deleted_at'), 'memories', ['deleted_at'], unique=False)
    # 向量近邻（cosine）
    op.execute("CREATE INDEX ix_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    # 中文关键词：pg_trgm 三元组
    op.execute("CREATE INDEX ix_memories_content_trgm ON memories USING gin (content gin_trgm_ops)")
    op.execute("CREATE INDEX ix_memories_subject_trgm ON memories USING gin (subject gin_trgm_ops)")

    op.create_table(
        'conversation_threads',
        sa.Column('thread_id', sa.String(length=64), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('rolling_summary', sa.Text(), nullable=True),
        sa.Column('turn_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('status', sa.String(length=16), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('thread_id'),
    )
    op.create_index(op.f('ix_conversation_threads_owner_id'), 'conversation_threads', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_conversation_threads_owner_id'), table_name='conversation_threads')
    op.drop_table('conversation_threads')
    op.execute("DROP INDEX IF EXISTS ix_memories_subject_trgm")
    op.execute("DROP INDEX IF EXISTS ix_memories_content_trgm")
    op.execute("DROP INDEX IF EXISTS ix_memories_embedding")
    op.drop_index(op.f('ix_memories_deleted_at'), table_name='memories')
    op.drop_index(op.f('ix_memories_meeting_id'), table_name='memories')
    op.drop_index(op.f('ix_memories_subject'), table_name='memories')
    op.drop_index(op.f('ix_memories_kind'), table_name='memories')
    op.drop_index(op.f('ix_memories_owner_id'), table_name='memories')
    op.drop_table('memories')