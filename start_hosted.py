"""Container entrypoint. Runtime credentials must be configured by deployment."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from app.config import public_origin

def validate_hosted():
    if not public_origin():raise RuntimeError('PUBLIC_BASE_URL must be set before hosted startup')
    if not os.getenv('MASTER_KEY') or not os.getenv('APP_TOKEN'):raise RuntimeError('MASTER_KEY and APP_TOKEN must be provided as hosting secrets')
    if len(os.environ['APP_TOKEN'])<32:raise RuntimeError('Use an APP_TOKEN with at least 32 characters')
    if not os.getenv('DATABASE_URL') and not Path(os.getenv('DATA_DIR','/data')).is_absolute():raise RuntimeError('Hosted DATA_DIR must be an absolute persistent volume mount')
    return int(os.getenv('PORT','8000'))
if __name__=='__main__':
    port=validate_hosted()
    data=Path(os.getenv('DATA_DIR','/data'));data.mkdir(mode=0o700,parents=True,exist_ok=True)
    # Railway mounts volumes owned by root. Prepare this private directory, then
    # drop privileges permanently before serving requests or launching browsers.
    if hasattr(os,'getuid') and os.getuid()==0:
        os.chown(data,10001,10001)
        for name in ('trialflow.db','trialflow.db-journal','trialflow.db-wal','trialflow.db-shm'):
            item=data/name
            if item.exists():os.chown(item,10001,10001,follow_symlinks=False)
        os.setgroups([]);os.setgid(10001);os.setuid(10001)
        os.environ['HOME']='/home/trialflow'
    import uvicorn
    uvicorn.run('app.main:app',host='0.0.0.0',port=port,workers=1,access_log=False,proxy_headers=True,forwarded_allow_ips='*')
