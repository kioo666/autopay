import asyncio, copy, json
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app import accounts, adapters, oauth, store
from app.main import app
from tests.test_core import env
H={'Authorization':'Bearer test-token'}

def reviewed():
    a=json.load(open('adapters/example.json'))
    a.update(reviewed=True,policy={'automation':'allowed','source_url':'https://example.com/terms','reviewed_on':date.today().isoformat(),'reason':'Official test fixture permits this workflow'})
    return a

def test_random_healthy_only(monkeypatch):
    for e in ['a@gmail.com','b@gmail.com','c@gmail.com']:store.secret_set('gmail:'+e,'{}')
    monkeypatch.setattr(accounts,'health',lambda e:{'usable':e=='b@gmail.com','reason':'fixture'})
    assert accounts.select(random_selection=True)=='b@gmail.com'
    with pytest.raises(ValueError):accounts.select('a@gmail.com')
    with pytest.raises(ValueError):accounts.select('missing@gmail.com')
    assert accounts.select('b@gmail.com')=='b@gmail.com'

def test_random_none(monkeypatch):
    store.secret_set('gmail:a@gmail.com','{}');monkeypatch.setattr(accounts,'health',lambda e:{'usable':False,'reason':'expired'})
    with pytest.raises(ValueError,match='No usable'):accounts.select(random_selection=True)

def test_application_manager():
    with TestClient(app) as c:
        r=c.post('/api/applications',headers=H,json={'id':'dynamic','name':'Dynamic','url':'https://example.com/signup'})
        assert r.status_code==201 and not r.json()['enabled']
        config=c.get('/api/applications/dynamic',headers=H).json()
        assert config['name']=='Dynamic'
        config=reviewed()
        assert c.put('/api/applications/dynamic',headers=H,json={'config':config}).json()['enabled']
        assert adapters.load('dynamic')['reviewed']
        assert c.delete('/api/applications/dynamic',headers=H).status_code==200
        assert c.get('/api/applications/dynamic',headers=H).status_code==404

def test_bad_urls():
    with TestClient(app) as c:
        for url in ['http://example.com','https://127.0.0.1/x','https://localhost/x','https://user:pass@example.com/x']:
            assert c.post('/api/applications',headers=H,json={'id':'bad','name':'Bad','url':url}).status_code==400

def test_review_policy_expiry_and_steps():
    a=reviewed();assert adapters.validate(a)
    for field,value in [('automation','forbidden'),('automation','unknown'),('reviewed_on','2020-01-01')]:
        bad=copy.deepcopy(a);bad['policy'][field]=value
        with pytest.raises(ValueError):adapters.validate(bad)
    bad=copy.deepcopy(a);bad['activation'][0]['reviewed_safe']=False
    with pytest.raises(ValueError):adapters.validate(bad)

def test_remove_and_active_protection():
    store.secret_set('gmail:a@gmail.com','sensitive-token');j=store.create('fixture','a@gmail.com','7 days')
    with TestClient(app) as c:
        store.update(j,status='running')
        assert c.delete('/api/emails/a@gmail.com',headers=H).status_code==409
        store.update(j,status='failed')
        assert c.delete('/api/emails/a@gmail.com',headers=H).json()['google_access_revoked'] is False
        assert not store.secret_get('gmail:a@gmail.com') and len(store.jobs())==1

def test_service_reservation_atomic():
    j=store.create_reserved('one','a@gmail.com','7 days','example.com','safe-password')
    with pytest.raises(Exception):store.create_reserved('two','b@gmail.com','7 days','example.com','other-password')
    assert len(store.jobs())==1 and store.reserved('example.com')
    assert store.secret_get('password:'+j)=='safe-password'

def test_start_resolves_mailbox_and_blocks_rotation(monkeypatch):
    store.app_save('dynamic',reviewed())
    store.secret_set('gmail:a@gmail.com','{}');store.secret_set('gmail:b@gmail.com','{}')
    checked=[]
    def healthy(email):checked.append(email);return {'usable':True,'reason':'fixture'}
    monkeypatch.setattr(accounts,'health',healthy)
    async def worker(jid,a,data):
        assert data['email'] in ['a@gmail.com','b@gmail.com']
        store.update(jid,status='completed')
    monkeypatch.setattr('app.main.run',worker)
    body={'adapter':'dynamic','random_selection':True,'name':'Real Owner','password':'long-password','eligible':True,'terms_accepted':True}
    with TestClient(app) as c:
        r=c.post('/api/jobs',headers=H,json=body);assert r.status_code==202
        assert r.json()['email'] in checked
        assert c.post('/api/jobs',headers=H,json=body).status_code==409
        assert c.put('/api/applications/dynamic',headers=H,json={'config':reviewed()}).status_code==400
        assert c.delete('/api/applications/dynamic',headers=H).status_code==409

def test_oauth_state_invalid_and_expired():
    with pytest.raises(ValueError):oauth.finish('bad','code')
    oauth.PENDING['expired']=(object(),-1)
    with pytest.raises(ValueError):oauth.finish('expired','code')
    assert 'expired' not in oauth.PENDING

def test_oauth_roundtrip(monkeypatch):
    class Creds:
        refresh_token='refresh-token'
        def has_scopes(self,scopes):return True
        def to_json(self):return '{"refresh_token":"secret"}'
    class Flow:
        credentials=Creds()
        def authorization_url(self,**kwargs):return ('https://accounts.google.com/test','state-unique')
        def fetch_token(self,code):assert code=='auth-code'
    flags={}
    def make(*args,**kwargs):flags.update(kwargs);return Flow()
    monkeypatch.setattr(oauth.Flow,'from_client_config',make)
    monkeypatch.setattr(oauth,'google_client_config',lambda:{'fixture':True})
    class Gmail:
        def users(self):return self
        def getProfile(self,**kwargs):return self
        def messages(self):return self
        def list(self,**kwargs):return self
        def execute(self):return {'emailAddress':'Real.Owner@gmail.com'}
    monkeypatch.setattr(oauth,'build',lambda *a,**kw:Gmail())
    assert oauth.start().startswith('https://accounts.google.com/')
    assert flags['autogenerate_code_verifier'] is True
    assert oauth.finish('state-unique','auth-code')=='real.owner@gmail.com'
    assert store.secret_get('gmail:real.owner@gmail.com')
    with pytest.raises(ValueError):oauth.finish('state-unique','auth-code')

def test_live_health_identity_and_errors(monkeypatch):
    class Gmail:
        def users(self):return self
        def getProfile(self,**kwargs):return self
        def messages(self):return self
        def list(self,**kwargs):return self
        def execute(self):return {'emailAddress':'owner@gmail.com'}
    monkeypatch.setattr(accounts.mail,'service',lambda _:Gmail())
    assert accounts.health('owner@gmail.com')['usable']
    assert not accounts.health('other@gmail.com')['usable']
    def fail(_):raise RuntimeError('do-not-leak-token')
    monkeypatch.setattr(accounts.mail,'service',fail)
    result=accounts.health('owner@gmail.com');assert not result['usable'] and 'do-not-leak' not in str(result)

def test_named_platforms_stopped():
    for name in ['chatgpt','canva','capcut','alight-motion']:
        s=adapters.summary(name,adapters.get(name));assert not s['enabled'] and s['reason']

def test_oauth_callback_denial_and_no_secret_logging():
    import logging
    from app.main import RedactOAuth
    record=logging.LogRecord('uvicorn.access',logging.INFO,'',0,'%s - "%s %s HTTP/%s" %d',('127.0.0.1','GET','/oauth/callback?code=secret&state=secret','1.1',200),None)
    RedactOAuth().filter(record);assert 'code=secret' not in record.getMessage()
    oauth.PENDING['denied']=(object(),999999999999)
    with TestClient(app) as c:
        r=c.get('/oauth/callback?error=access_denied&state=denied')
        assert r.status_code==400 and 'denied' not in oauth.PENDING
        assert r.headers['cache-control']=='no-store'

def test_random_endpoint_and_health_failure_prevents_job(monkeypatch):
    store.secret_set('gmail:a@gmail.com','{}');store.app_save('dynamic',reviewed())
    monkeypatch.setattr(accounts,'health',lambda e:{'email':e,'usable':False,'reason':'Reconnect Gmail'})
    with TestClient(app) as c:
        assert c.post('/api/emails/select',headers=H,json={'random_selection':True}).status_code==400
        assert c.post('/api/emails/a@gmail.com/check',headers=H).json()['usable'] is False
        data={'adapter':'dynamic','email':'a@gmail.com','name':'Owner','password':'long-password','eligible':True,'terms_accepted':True}
        assert c.post('/api/jobs',headers=H,json=data).status_code==400
        assert not store.jobs() and not store.reserved('example.com')

def test_strict_payment_boolean():
    a=reviewed();a['no_payment_required']='false'
    with pytest.raises(ValueError,match='boolean'):adapters.validate(a)
    a=reviewed();a['reviewed']='true'
    with pytest.raises(ValueError):adapters.validate(a)

def test_known_service_aliases():
    assert adapters.service_key({'signup_url':'https://auth.openai.com/signup'})==adapters.service_key({'signup_url':'https://chatgpt.com/signup'})
    assert adapters.service_key({'signup_url':'https://www.example.com/signup'})==adapters.service_key({'signup_url':'https://example.com/other'})
