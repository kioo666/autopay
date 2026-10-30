"""Loopback Google OAuth with PKCE, expiring single-use state and no token URLs."""
import os, time, threading
from urllib.parse import urlparse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.mail import SCOPES
from app import store
from app.config import redirect_uri, google_client_config
PENDING={}
LOCK=threading.Lock()
def start():
    redirect=redirect_uri()
    flow=Flow.from_client_config(google_client_config(),scopes=SCOPES,redirect_uri=redirect,autogenerate_code_verifier=True)
    url,state=flow.authorization_url(access_type='offline',prompt='consent select_account')
    with LOCK:
        expired=[s for s,(_,t) in PENDING.items() if t<time.monotonic()]
        for s in expired:PENDING.pop(s,None)
        if len(PENDING)>=10: raise ValueError('Too many pending OAuth requests')
        PENDING[state]=(flow,time.monotonic()+600)
    return url

def finish(state,code):
    with LOCK: pending=PENDING.pop(state,None)
    if not pending or pending[1]<time.monotonic(): raise ValueError('OAuth state invalid, expired or already used')
    flow=pending[0]; flow.fetch_token(code=code)
    creds=flow.credentials
    granted=getattr(creds,'granted_scopes',None)
    if (granted is not None and not set(SCOPES)<=set(granted)) or not creds.has_scopes(SCOPES): raise ValueError('Read-only Gmail permission required')
    if not creds.refresh_token: raise ValueError('Offline access missing; reconnect and consent again')
    api=build('gmail','v1',credentials=creds,cache_discovery=False)
    api.users().messages().list(userId='me',maxResults=1).execute()
    email=api.users().getProfile(userId='me').execute()['emailAddress'].lower()
    store.secret_set('gmail:'+email,creds.to_json())
    return email
