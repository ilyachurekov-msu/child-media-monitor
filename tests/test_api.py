from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_openapi_contract():
    paths = client.get('/openapi.json').json()['paths']
    for path in ['/posts', '/posts/{post_id}', '/topics', '/regions/{region_id}/summary', '/trends', '/alerts', '/search', '/sources/status']:
        assert '/api/v1/media' + path in paths


def test_validation_prevents_invalid_query():
    assert client.get('/api/v1/media/posts?limit=101').status_code == 422
    assert client.get('/api/v1/media/posts/not-a-uuid').status_code == 422


def test_writes_need_auth():
    assert client.post('/api/v1/media/reprocess').status_code == 401


def test_public_contract_omits_raw_identifiers():
    schema = client.get('/openapi.json').json()['components']['schemas']['PostOut']['properties']
    assert not {'raw_metadata', 'author_display', 'external_id', 'text_hash'} & schema.keys()


def test_privacy_queue_requires_auth():
    assert client.get('/api/v1/media/privacy/reviews').status_code == 401
