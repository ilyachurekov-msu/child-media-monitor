"""Synthetic CI data only. Uses exactly the production collector and processor."""
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import update
from app.db import Session
from app.models import Source, SourceConfig, Post, PostTopic, now
from app.identity import source_id
from app.workers.main import collect, process_batch


def main():
    sid = source_id('rss', 'https://example.org/ci-feed')
    with Session.begin() as db:
        db.execute(update(SourceConfig).values(enabled=False))
        db.merge(Source(source_id=sid, source_type='rss', name='CI synthetic', url='https://example.org/ci-feed'))
        db.flush()
        db.merge(SourceConfig(source_id=sid, enabled=False))
    for fixture in ['public.xml', 'sensitive.xml']:
        body = Path('tests/fixtures', fixture).read_bytes()
        with patch('app.workers.main.allowed', return_value=True), patch('app.workers.main.fetch', return_value=(200, {}, body)):
            collect(sid)
    process_batch()
    with Session.begin() as db:
        db.execute(update(Post).where(Post.source_id == sid).values(published_at=now()))
        db.execute(update(PostTopic).values(review_status='confirmed'))


if __name__ == '__main__': main()
