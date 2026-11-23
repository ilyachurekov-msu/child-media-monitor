import os
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, delete
from app.db import Session, engine
from app.models import Source, SourceConfig, Post, PrivacyCheck, PostTopic, Embedding
from app.identity import source_id, post_id
from app.workers.main import collect, process_batch
from app.api.main import app
from app.config import settings

pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='PostgreSQL required')
FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def fixture_source():
    sid = source_id('rss', 'https://example.org/fixture-feed')
    with Session.begin() as db:
        db.execute(delete(Post).where(Post.source_id == sid))
        db.merge(Source(source_id=sid, source_type='rss', name='Synthetic fixtures', url='https://example.org/fixture-feed'))
        db.flush()
        db.merge(SourceConfig(source_id=sid, enabled=False))
    yield sid


def load(sid, filename='public.xml', body=None):
    body = body or (FIXTURES / filename).read_bytes()
    with patch('app.workers.main.allowed', return_value=True), patch('app.workers.main.fetch', return_value=(200, {}, body)):
        collect(sid)


def test_database_schema():
    with engine.connect() as db:
        assert db.scalar(text("SELECT extname FROM pg_extension WHERE extname='vector'")) == 'vector'
        assert int(db.scalar(text('SHOW server_version_num'))) // 10000 == 16
        indexes = db.scalars(text("SELECT indexname FROM pg_indexes WHERE schemaname IN ('media','core')")).all()
        assert {'ix_posts_fts', 'ix_privacy_fts', 'ix_posts_hash', 'ix_pr_region', 'ix_pt_topic'} <= set(indexes)
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == '0003'


def test_rss_storage_update_privacy_and_api(fixture_source):
    sid = fixture_source
    load(sid); load(sid)
    pid = post_id(sid, 'fixture-public-1')
    with Session() as db:
        assert len(db.scalars(select(Post).where(Post.source_id == sid)).all()) == 2
        assert db.get(Post, pid).title == 'В Москве открыли школу'
        assert db.get(PrivacyCheck, pid).status == 'allowed'
    updated = (FIXTURES / 'public.xml').read_bytes().replace('новую школу'.encode(), 'новую школу после ремонта'.encode())
    load(sid, body=updated)
    engine.dispose()  # New physical connection: data survives client restart.
    with Session() as db:
        assert 'после ремонта' in db.get(Post, pid).text
        assert len(db.scalars(select(Post).where(Post.source_id == sid)).all()) == 2
    load(sid, 'sensitive.xml')
    process_batch()
    client = TestClient(app)
    prefix = '/api/v1/media'
    assert client.get('/health').status_code == 200
    result = client.get(prefix + '/posts', params={'source_id': str(sid)}).json()
    assert result['total'] == 2
    hidden = post_id(sid, 'fixture-sensitive-1')
    assert client.get(prefix + '/posts/' + str(hidden)).status_code == 404
    for path in ['/posts', '/search?q=школа', '/digest', '/trends', '/sources/status', '/regions/RU-77/summary', '/alerts', '/topics']:
        response = client.get(prefix + path)
        assert response.status_code == 200, path
        assert 'example@example.invalid' not in response.text
        assert 'Тестов' not in response.text
    assert client.get(prefix + '/search?q=школа').json()['total'] >= 1
    assert client.get(prefix + '/posts', params={'topic_id': 'education', 'region_id': 'RU-77'}).json()['total'] >= 1
    assert client.get(prefix + '/search', params={'q': 'example@example.invalid'}).json()['total'] == 0
    assert client.get(prefix + '/search', params={'q': 'школа', 'mode': 'semantic'}).status_code == 503
    # Protect a rejected manual label across a full reprocessing pass.
    settings.admin_token = 'synthetic-ci-admin'
    correction = client.post(prefix + '/posts/' + str(pid) + '/reviews', json={
        'object_type': 'topic', 'label': 'education', 'accepted': False, 'reason': 'Синтетическая проверка'},
        headers={'Authorization': 'Bearer synthetic-ci-admin'})
    assert correction.status_code == 200
    with Session.begin() as db: db.get(Post, pid).processing_status = 'pending'
    process_batch()
    with Session() as db:
        assert db.get(PostTopic, (pid, 'education')).review_status == 'rejected'
        db.merge(Embedding(post_id=pid, model='synthetic', model_version='test-only', vector=[.1] * 384))
        db.commit()
        assert len(db.get(Embedding, (pid, 'synthetic', 'test-only')).vector) == 384
