"""Streamlit widget smoke with deterministic API responses, no news network."""
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_all_sections():
    import httpx
    def get(url, **kwargs):
        path = url.split('/api/v1/media')[-1]
        body = {'items': [], 'total': 0} if path == '/posts' else []
        return httpx.Response(200, json=body, request=httpx.Request('GET', url))
    with patch('httpx.get', side_effect=get):
        ui = AppTest.from_file(Path('app/ui/main.py').resolve()).run(timeout=30)
        assert not ui.exception
        for page in ui.sidebar.radio[0].options:
            ui.sidebar.radio[0].set_value(page).run(timeout=30)
            assert not ui.exception
