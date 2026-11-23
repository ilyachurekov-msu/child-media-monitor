"""Run against a migrated disposable DB: TEST_DATABASE_URL=... pytest."""
import os
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models import Source, Post, now
from app.identity import source_id, post_id, text_hash


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Disposable PostgreSQL 16 not configured')
def test_storage_idempotence():
    engine = create_engine(os.environ['TEST_DATABASE_URL'])
    with engine.connect() as connection:
        tx = connection.begin()
        try:
            db = Session(bind=connection)
            sid = source_id('rss', 'https://example.org/test-feed')
            db.execute(insert(Source).values(source_id=sid, source_type='rss', name='Test').on_conflict_do_nothing())
            pid = post_id(sid, 'entry')
            values = dict(post_id=pid, source_id=sid, external_id='entry', source_type='rss', url='https://example.org/test', text='Тест', text_hash=text_hash('Тест'), published_at=now())
            for _ in range(2): db.execute(insert(Post).values(**values).on_conflict_do_nothing())
            assert len(db.scalars(select(Post).where(Post.post_id == pid)).all()) == 1
        finally:
            tx.rollback()
