import os, sqlite3, json, uuid
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from dotenv import load_dotenv
load_dotenv()
def now(): return datetime.now(timezone.utc).isoformat()
SCHEMA='CREATE TABLE IF NOT EXISTS secrets (id TEXT PRIMARY KEY, value BLOB); CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, app TEXT, email TEXT, status TEXT, registration TEXT, verification TEXT, trial TEXT, duration TEXT, activated TEXT, created TEXT, events TEXT); CREATE UNIQUE INDEX IF NOT EXISTS one_claim ON jobs(app,email);CREATE TABLE IF NOT EXISTS applications (id TEXT PRIMARY KEY, config TEXT NOT NULL); CREATE TABLE IF NOT EXISTS claims (service TEXT PRIMARY KEY, job_id TEXT NOT NULL, created TEXT NOT NULL);'
@contextmanager
def db():
    if os.getenv('DATABASE_URL'):
        import psycopg
        from psycopg.rows import dict_row
        from app.postgres import Connection
        with psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row,connect_timeout=10) as raw:
            c=Connection(raw)
            c.executescript(SCHEMA)
            yield c
        return
    root=Path(os.getenv('DATA_DIR','data')); root.mkdir(mode=0o700,parents=True,exist_ok=True)
    c=sqlite3.connect(root/'trialflow.db'); c.row_factory=sqlite3.Row
    c.executescript(SCHEMA)
    try:
        with c: yield c
    finally: c.close()
def cipher(): return Fernet(os.environ['MASTER_KEY'].encode())
def secret_set(key,value):
    with db() as c: c.execute('INSERT OR REPLACE INTO secrets VALUES (?,?)',(key,cipher().encrypt(value.encode())))
def secret_get(key):
    with db() as c: row=c.execute('SELECT value FROM secrets WHERE id=?',(key,)).fetchone()
    return cipher().decrypt(row[0]).decode() if row else None
def jobs():
    with db() as c: return [dict(r)|{'events':json.loads(r['events'])} for r in c.execute('SELECT * FROM jobs ORDER BY created DESC')]
def create(app,email,duration):
    jid=uuid.uuid4().hex
    with db() as c: c.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)',(jid,app,email,'queued','pending','pending','pending',duration,None,now(),'[]'))
    return jid
def update(jid,**values):
    allowed={'status','registration','verification','trial','activated'}
    assert values.keys() <= allowed
    with db() as c: c.execute('UPDATE jobs SET '+','.join(k+'=?' for k in values)+' WHERE id=?',(*values.values(),jid))
def event(jid,message):
    with db() as c:
        row=c.execute('SELECT events FROM jobs WHERE id=?',(jid,)).fetchone()
        ev=json.loads(row[0]); ev.append({'time':now(),'message':message})
        c.execute('UPDATE jobs SET events=? WHERE id=?',(json.dumps(ev),jid))

def secret_delete(key):
    with db() as c: c.execute('DELETE FROM secrets WHERE id=?',(key,))
def accounts():
    with db() as c:
        rows=c.execute("SELECT id FROM secrets WHERE id LIKE 'gmail:%' ORDER BY id").fetchall()
        return [{'email':r[0][6:]} for r in rows]
def app_save(slug,config):
    with db() as c: c.execute('INSERT OR REPLACE INTO applications VALUES (?,?)',(slug,json.dumps(config)))
def app_get(slug):
    with db() as c: row=c.execute('SELECT config FROM applications WHERE id=?',(slug,)).fetchone()
    return json.loads(row[0]) if row else None
def app_all():
    with db() as c: return {r[0]:json.loads(r[1]) for r in c.execute('SELECT id,config FROM applications')}
def app_delete(slug):
    with db() as c: c.execute('DELETE FROM applications WHERE id=?',(slug,))
def reserve(service,jid):
    with db() as c: c.execute('INSERT INTO claims VALUES (?,?,?)',(service,jid,now()))
def reserved(service):
    with db() as c: return c.execute('SELECT 1 FROM claims WHERE service=?',(service,)).fetchone() is not None

def create_reserved(app,email,duration,service,password):
    jid=uuid.uuid4().hex
    encrypted=cipher().encrypt(password.encode())
    with db() as c:
        c.execute('INSERT INTO claims VALUES (?,?,?)',(service,jid,now()))
        c.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)',(jid,app,email,'queued','pending','pending','pending',duration,None,now(),'[]'))
        c.execute('INSERT INTO secrets VALUES (?,?)',('password:'+jid,encrypted))
    return jid
