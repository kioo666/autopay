import json
import pytest
from app import config
from start_hosted import validate_hosted
from tests.test_core import env

def client(kind='web'):
    return {kind:{'client_id':'fixture-id','client_secret':'fixture-secret','auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token'}}

def test_https_callback(monkeypatch):
    monkeypatch.setenv('PUBLIC_BASE_URL','https://trialflow.example.com')
    monkeypatch.setenv('GOOGLE_CLIENT_JSON',json.dumps(client()))
    assert config.redirect_uri()=='https://trialflow.example.com/oauth/callback'
    assert 'web' in config.google_client_config()

def test_reject_origin_and_external_token_endpoint(monkeypatch):
    for bad in ['http://host.example','https://user:pass@host.example','https://host.example/path','https://localhost']:
        monkeypatch.setenv('PUBLIC_BASE_URL',bad)
        with pytest.raises(ValueError):config.public_origin()
    monkeypatch.setenv('PUBLIC_BASE_URL','https://trialflow.example')
    c=client();c['web']['token_uri']='https://evil.example/token';monkeypatch.setenv('GOOGLE_CLIENT_JSON',json.dumps(c))
    with pytest.raises(ValueError):config.google_client_config()
    monkeypatch.setenv('GOOGLE_CLIENT_JSON',json.dumps(client('installed')))
    with pytest.raises(ValueError):config.google_client_config()

def test_hosted_startup_requires_persistent_config(monkeypatch):
    monkeypatch.setenv('PUBLIC_BASE_URL','https://trialflow.example')
    monkeypatch.setenv('DATA_DIR','/data');monkeypatch.setenv('APP_TOKEN','x'*40)
    assert validate_hosted()==8000
    monkeypatch.setenv('APP_TOKEN','short')
    with pytest.raises(RuntimeError):validate_hosted()

def test_browser_session_and_csrf():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.access import COOKIE,signed_session
    with TestClient(app) as c:
        r=c.post('/api/session',headers={'Authorization':'Bearer test-token'})
        assert r.status_code==200 and 'HttpOnly' in r.headers['set-cookie']
        assert c.get('/api/emails').status_code==200
        assert c.post('/api/emails/select',json={'random_selection':True},headers={'Origin':'https://evil.example'}).status_code==403
        assert c.post('/api/logout',headers={'Origin':'http://testserver'}).status_code==200
        assert c.get('/api/emails').status_code==401
        c.cookies.set(COOKIE,signed_session(1))
        assert c.get('/api/emails').status_code==401
