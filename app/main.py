import asyncio, os, secrets, sqlite3, json, logging
from pathlib import Path
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from app import store, accounts, oauth, adapters
from app.engine import run
from app.config import public_origin
from app.access import auth, signed_session, COOKIE, TTL
class RedactOAuth(logging.Filter):
    def filter(self, record):
        if isinstance(record.args,tuple) and len(record.args)==5:
            args=list(record.args)
            if isinstance(args[2],str) and args[2].startswith('/oauth/callback?'):
                args[2]='/oauth/callback?[redacted]'; record.args=tuple(args)
        return True
logging.getLogger('uvicorn.access').addFilter(RedactOAuth())
TASKS=set()
REGISTRY=asyncio.Lock()
@asynccontextmanager
async def lifespan(app):
    if not os.getenv('APP_TOKEN') or not os.getenv('MASTER_KEY'):raise RuntimeError('Run setup_local.py first')
    store.cipher()
    for j in store.jobs():
        try:
            service=adapters.service_key(adapters.get(j['app']))
            if not store.reserved(service):store.reserve(service,j['id'])
        except (ValueError,KeyError,sqlite3.IntegrityError):pass
        if j['status'] in ('queued','running'):
            store.update(j['id'],status='interrupted');store.event(j['id'],'Server interrupted; inspect account manually. No retry.')
    yield
    pending=list(TASKS)
    for t in pending:t.cancel()
    if pending:await asyncio.gather(*pending,return_exceptions=True)
app=FastAPI(title='TrialFlow Multi',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver']+([urlparse(public_origin()).hostname,'healthcheck.railway.app'] if public_origin() else []))
@app.middleware('http')
async def headers(request,call_next):
    r=await call_next(request)
    r.headers['Cache-Control']='no-store';r.headers['X-Content-Type-Options']='nosniff';r.headers['Referrer-Policy']='no-referrer'
    r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return r

class Claim(BaseModel):
    adapter:str=Field(max_length=80)
    email:str|None=Field(default=None,max_length=254)
    random_selection:bool=False
    name:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=10,max_length=128)
    eligible:bool
    terms_accepted:bool
class Application(BaseModel):
    id:str=Field(pattern=r'^[a-z0-9][a-z0-9_-]{0,79}$')
    name:str=Field(min_length=1,max_length=100)
    url:str=Field(max_length=2000)
class Config(BaseModel):
    config:dict
class EmailSelection(BaseModel):
    email:str|None=None
    random_selection:bool=False
@app.get('/')
def index():return FileResponse('app/static/index.html')
@app.post('/api/session',dependencies=[Depends(auth)])
def session():
    response=JSONResponse({'authenticated':True})
    response.set_cookie(COOKIE,signed_session(),max_age=TTL,httponly=True,secure=bool(public_origin()),samesite='strict',path='/')
    return response
@app.post('/api/logout',dependencies=[Depends(auth)])
def logout():
    response=JSONResponse({'logged_out':True});response.delete_cookie(COOKIE,path='/');return response
@app.get('/healthz')
def healthz():return {'status':'ok','service':'trialflow'}
@app.get('/api/readiness',dependencies=[Depends(auth)])
def readiness():
    from app.readiness import inspect
    return inspect()
@app.get('/api/jobs',dependencies=[Depends(auth)])
def jobs():return store.jobs()
@app.get('/api/adapters',dependencies=[Depends(auth)])
def app_list():return [adapters.summary(n,a) for n,a in adapters.all_configs().items()]
@app.post('/api/applications',status_code=201,dependencies=[Depends(auth)])
async def app_create(c:Application):
    async with REGISTRY:
        if c.id in adapters.all_configs():raise HTTPException(409,'Application ID already exists')
        try:host=adapters.url_check(c.url)
        except ValueError as e:raise HTTPException(400,str(e))
        template=json.loads(open('adapters/example.json').read())
        template.update(name=c.name,signup_url=c.url,trial_url=c.url,eligibility_url=c.url,terms_url=c.url,allowed_hosts=[host],verification_hosts=[host],reviewed=False,policy={'automation':'unknown','reason':'Review official automation permission and trial terms before enabling','source_url':c.url,'reviewed_on':''})
        store.app_save(c.id,template)
        return adapters.summary(c.id,template)
@app.get('/api/applications/{slug}',dependencies=[Depends(auth)])
def app_config(slug:str):
    try:return adapters.get(slug)
    except ValueError as e:raise HTTPException(404,str(e))
@app.put('/api/applications/{slug}',dependencies=[Depends(auth)])
async def app_update(slug:str,c:Config):
    async with REGISTRY:
        try:
            original=adapters.get(slug)
            if any(j['app']==slug for j in store.jobs()):raise ValueError('Application with process history is immutable; preserve audit and claim scope')
            if len(json.dumps(c.config))>64000:raise ValueError('Configuration too large')
            adapters.url_check(c.config['signup_url'])
            for field in ['trial_url','terms_url','eligibility_url']:
                if c.config.get(field):adapters.url_check(c.config[field])
            if c.config.get('reviewed'):adapters.validate(c.config)
        except (ValueError,KeyError,TypeError) as e:raise HTTPException(400,str(e))
        store.app_save(slug,c.config);return adapters.summary(slug,c.config)
@app.delete('/api/applications/{slug}',dependencies=[Depends(auth)])
async def app_delete(slug:str):
    async with REGISTRY:
        if any(j['app']==slug for j in store.jobs()):raise HTTPException(409,'Application has history; deletion is disabled to preserve audit and claim limits')
        if (Path('adapters')/(slug+'.json')).is_file() or not store.app_get(slug):raise HTTPException(400,'Bundled presets cannot be deleted; use a custom application')
        store.app_delete(slug);return {'deleted':True}
@app.get('/api/emails',dependencies=[Depends(auth)])
def emails():return store.accounts()
@app.post('/api/emails/select',dependencies=[Depends(auth)])
async def select(c:EmailSelection):
    async with REGISTRY:
        try:return {'email':await asyncio.to_thread(accounts.select,c.email,c.random_selection)}
        except ValueError as e:raise HTTPException(400,str(e))
@app.post('/api/emails/{email}/check',dependencies=[Depends(auth)])
async def check(email:str):
    if email not in [a['email'] for a in store.accounts()]:raise HTTPException(404,'Gmail is not connected')
    return await asyncio.to_thread(accounts.health,email)
@app.delete('/api/emails/{email}',dependencies=[Depends(auth)])
async def remove_email(email:str):
    async with REGISTRY:
        if any(j['email']==email and j['status'] in ('running','queued') for j in store.jobs()):raise HTTPException(409,'Gmail is in use by an active process')
        store.secret_delete('gmail:'+email);return {'removed_locally':True,'google_access_revoked':False}
@app.post('/api/oauth/start',dependencies=[Depends(auth)])
def oauth_start():
    try:return {'authorization_url':oauth.start()}
    except Exception as e:raise HTTPException(400,'Cannot start Google OAuth ('+type(e).__name__+'). Check credentials.json and callback settings.')
@app.get('/oauth/callback',response_class=HTMLResponse)
def oauth_callback(state:str='',code:str='',error:str=''):
    try:
        if error or not code:
            with oauth.LOCK:oauth.PENDING.pop(state,None)
            raise ValueError('OAuth consent was not completed')
        oauth.finish(state,code)
        return '<!doctype html><meta name="referrer" content="no-referrer"><title>Gmail connected</title><h1>Gmail terhubung</h1><p>Tutup tab ini, lalu tekan Refresh Gmail di dashboard.</p>'
    except Exception as e:
        return HTMLResponse('<h1>OAuth gagal</h1><p>State kedaluwarsa, izin ditolak, atau konfigurasi tidak sesuai. Mulai ulang dari dashboard. Detail: '+type(e).__name__+'</p>',status_code=400)
@app.post('/api/jobs',status_code=202,dependencies=[Depends(auth)])
async def claim(c:Claim):
    if not c.eligible or not c.terms_accepted:raise HTTPException(400,'Confirm eligibility and platform terms first')
    async with REGISTRY:
        if len(TASKS)>=int(os.getenv('MAX_ACTIVE_JOBS','3')):raise HTTPException(429,'Active process limit reached')
        try:a=adapters.load(c.adapter)
        except (ValueError,KeyError,TypeError) as e:raise HTTPException(400,'Application stopped: '+str(e))
        service=adapters.service_key(a)
        if store.reserved(service):raise HTTPException(409,'This service already has a process for this owner. Switching Gmail does not reset trial eligibility; inspect history manually.')
        try:email=await asyncio.to_thread(accounts.select,c.email.lower() if c.email else None,c.random_selection)
        except ValueError as e:raise HTTPException(400,str(e))
        try:jid=store.create_reserved(c.adapter,email,a.get('duration','Unknown'),service,c.password)
        except sqlite3.IntegrityError:raise HTTPException(409,'Duplicate service/email process; automatic repeat claims disabled')
        store.event(jid,'Selected connected Gmail; live API health check passed. Policy review passed.')
        task=asyncio.create_task(run(jid,a,{'email':email,'name':c.name,'password':c.password}))
        TASKS.add(task);task.add_done_callback(TASKS.discard)
        return {'id':jid,'email':email}
