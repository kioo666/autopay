from contextlib import contextmanager
from types import SimpleNamespace
from app import readiness
from tests.test_core import env


def test_prerequisites_are_separate_and_secret_free(monkeypatch, tmp_path):
    @contextmanager
    def browser():
        yield SimpleNamespace(chromium=SimpleNamespace(executable_path=str(tmp_path/'missing-browser')))
    monkeypatch.setattr(readiness, 'sync_playwright', browser)
    monkeypatch.setattr(readiness, 'google_client_config', lambda: (_ for _ in ()).throw(ValueError('secret must never appear')))
    monkeypatch.setattr(readiness.store, 'accounts', lambda: [{'email':'private@example.com'}])
    monkeypatch.setattr(readiness.adapters, 'all_configs', lambda: {})
    result = readiness.inspect()
    assert not result['ready']
    assert {c['id']:c['ready'] for c in result['checks']} == {'oauth':False,'gmail':True,'browser':False,'adapters':False}
    assert 'private@example.com' not in str(result)
    assert 'secret must never appear' not in str(result)


def test_readiness_requires_owner_token(env):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        assert client.get('/api/readiness').status_code == 401
