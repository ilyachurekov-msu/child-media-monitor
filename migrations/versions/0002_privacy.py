"""Separate safe derivatives, fail-closed default for existing posts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '0002'
down_revision = '0001'


def upgrade():
    op.create_table('privacy_checks',
        sa.Column('post_id', UUID(as_uuid=True), sa.ForeignKey('media.posts.post_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('input_hash', sa.Text(), nullable=False),
        sa.Column('safe_title', sa.Text(), nullable=False),
        sa.Column('safe_text', sa.Text(), nullable=False),
        sa.Column('findings', JSONB(), nullable=False),
        sa.Column('risk', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('method_version', sa.Text(), nullable=False),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True)), schema='media')
    op.create_index('ix_privacy_checks_status', 'privacy_checks', ['status'], schema='media')
    op.execute("CREATE INDEX ix_privacy_fts ON media.privacy_checks USING gin(to_tsvector('russian', safe_title || ' ' || safe_text))")
    op.execute("UPDATE media.posts SET processing_status = 'pending'")


def downgrade():
    op.drop_table('privacy_checks', schema='media')
