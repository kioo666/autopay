from app.postgres import sql,Row

def test_postgres_translation():
    assert sql('SELECT id FROM jobs WHERE id=?')=='SELECT id FROM jobs WHERE id=%s'
    assert 'BYTEA' in sql('CREATE TABLE secrets (value BLOB)')
    assert 'ON CONFLICT (id)' in sql('INSERT OR REPLACE INTO secrets VALUES (?,?)')
    assert 'ON CONFLICT (id)' in sql('INSERT OR REPLACE INTO applications VALUES (?,?)')
    r=Row({'id':'job','status':'queued'})
    assert r[0]=='job' and r['status']=='queued' and dict(r)=={'id':'job','status':'queued'}
