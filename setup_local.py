from pathlib import Path
import secrets
from cryptography.fernet import Fernet
p=Path('.env')
if p.exists():
    raise SystemExit('.env already exists; keep your existing encryption key.')
p.write_text(f'MASTER_KEY={Fernet.generate_key().decode()}\nAPP_TOKEN={secrets.token_urlsafe(32)}\nHEADLESS=false\nGOOGLE_CLIENT_FILE=credentials.json\nDATA_DIR=data\nOAUTH_REDIRECT_URI=http://127.0.0.1:8000/oauth/callback\n')
p.chmod(0o600)
print('Configured. Keep .env private and back up its encryption key.')
