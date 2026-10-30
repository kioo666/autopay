import asyncio, base64, json, sqlite3
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from app import store
from app.mail import extract, body
from app.adapters import load
from app.main import app
@pytest.fixture(autouse=True)
def env(tmp_path,monkeypatch):
    monkeypatch.setenv('DATA_DIR',str(tmp_path)); monkeypatch.setenv('MASTER_KEY',Fernet.generate_key().decode()); monkeypatch.setenv('APP_TOKEN','test-token')
def test_encryption():
    store.secret_set('password','private-password'); assert store.secret_get('password')=='private-password'
    with store.db() as c: assert b'private-password' not in c.execute('SELECT value FROM secrets').fetchone()[0]
def test_history_and_duplicate():
    j=store.create('app','owner@example.com','7 days');store.event(j,'started');store.update(j,status='completed')
    assert store.jobs()[0]['events'][0]['message']=='started'
    with pytest.raises(sqlite3.IntegrityError):store.create('app','owner@example.com','7 days')
def test_extract():
    result=extract('OTP: 123456 <a href="https://safe.test/verify?t=1&amp;x=2">verify</a>',['safe.test'],r'OTP: (\d{6})')
    assert result=={'link':'https://safe.test/verify?t=1&x=2','otp':'123456'}
    assert extract('https://safe.test.evil/verify',['safe.test'],r'(\d{6})')['link'] is None
    assert extract('https://safe.test/a https://safe.test/b',['safe.test'],r'(\d{6})')['link'] is None
def test_mime():
    text='OTP: 123456';p={'parts':[{'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode(text.encode()).decode()}}]}
    assert text in body(p)
def test_unreviewed():
    with pytest.raises(ValueError):load('example')
    with pytest.raises(ValueError):load('../secret')
def test_api_auth_and_restart():
    j=store.create('app','owner@example.com','7 days')
    with TestClient(app) as c:
        assert c.get('/').status_code==200
        assert c.get('/api/jobs').status_code==401
        h={'Authorization':'Bearer test-token'}
        assert c.get('/api/jobs',headers=h).json()[0]['status']=='interrupted'
        assert all(not a['enabled'] for a in c.get('/api/adapters',headers=h).json())
        assert c.post('/api/jobs',headers=h,json={'adapter':'example','name':'Owner','email':'owner@example.com','password':'longpassword','eligible':False,'terms_accepted':True}).status_code==400
