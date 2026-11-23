import httpx

base = 'http://localhost:8000'
assert httpx.get(base + '/health').status_code == 200
prefix = base + '/api/v1/media'
data = httpx.get(prefix + '/posts').json()
assert data['total'] >= 2
assert any(p['title'] == 'В Москве открыли школу' for p in data['items'])
for path in ['/topics', '/regions', '/regions/RU-77/summary', '/trends', '/alerts', '/search?q=школа', '/sources/status', '/digest']:
    response = httpx.get(prefix + path)
    assert response.status_code == 200, path
    assert 'example@example.invalid' not in response.text
    assert 'Тестов' not in response.text
assert httpx.get('http://localhost:8501/_stcore/health').status_code == 200
