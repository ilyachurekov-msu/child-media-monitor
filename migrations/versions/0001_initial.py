"""Initial contract 1.0.0. Snapshot is immutable; subsequent changes need new revisions."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE SCHEMA IF NOT EXISTS core')
    op.execute('CREATE SCHEMA IF NOT EXISTS media')
    # DDL snapshot is frozen alongside this revision, never imported from current models.
    from pathlib import Path
    ddl = Path(__file__).with_name('0001_schema.sql').read_text(encoding='utf-8')
    for statement in ddl.split(';'):
        if statement.strip(): op.execute(sa.text(statement))
    op.execute("CREATE INDEX ix_posts_fts ON media.posts USING gin(to_tsvector('russian', coalesce(title,'') || ' ' || text))")


def downgrade():
    op.execute('DROP SCHEMA media CASCADE')
    # Shared core dictionary is intentionally retained.
