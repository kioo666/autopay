"""Explicit public origin, never derived from untrusted request Host headers."""
import os, json
from urllib.parse import urlparse

def public_origin():
    value=(os.getenv('PUBLIC_BASE_URL') or os.getenv('RENDER_EXTERNAL_URL','')).rstrip('/')
    if not value:return None
    u=urlparse(value)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:
        raise ValueError('PUBLIC_BASE_URL must be a public HTTPS origin')
    if u.hostname in ('localhost','127.0.0.1') or u.hostname.endswith('.local'):raise ValueError('Hosted origin cannot be localhost')
    return value

def redirect_uri():
    origin=public_origin()
    if origin:return origin+'/oauth/callback'
    value=os.getenv('OAUTH_REDIRECT_URI','http://127.0.0.1:8000/oauth/callback')
    u=urlparse(value)
    if u.hostname!='127.0.0.1' or u.scheme!='http' or u.path!='/oauth/callback' or u.username or u.query or u.fragment:
        raise ValueError('Local callback must use 127.0.0.1 /oauth/callback; hosted mode requires PUBLIC_BASE_URL')
    return value

def google_client_config():
    raw=os.getenv('GOOGLE_CLIENT_JSON')
    if raw:
        config=json.loads(raw)
    else:
        with open(os.getenv('GOOGLE_CLIENT_FILE','credentials.json')) as f:config=json.load(f)
    kind='web' if 'web' in config else 'installed'
    client=config.get(kind,{})
    if not client.get('client_id') or not client.get('client_secret'):raise ValueError('Google OAuth client is incomplete')
    if public_origin() and kind!='web':raise ValueError('Hosted Gmail requires Google OAuth client type Web application')
    # Do not permit a client config to redirect credentials to arbitrary endpoints.
    if client.get('auth_uri')!='https://accounts.google.com/o/oauth2/auth' or client.get('token_uri')!='https://oauth2.googleapis.com/token':
        raise ValueError('Google OAuth official endpoints required')
    return config
