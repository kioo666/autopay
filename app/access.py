"""Single-owner, signed HttpOnly browser session; secrets never go in server URLs."""
import os, time, hmac, hashlib, secrets
from fastapi import HTTPException, Request
from app.config import public_origin
COOKIE='trialflow_session'
TTL=12*60*60

def signed_session(expires=None):
    expiry=str(int(expires or time.time()+TTL))
    sig=hmac.new(os.environ['APP_TOKEN'].encode(),('trialflow:'+expiry).encode(),hashlib.sha256).hexdigest()
    return expiry+'.'+sig

def valid_session(value):
    try:
        expiry,_=value.split('.',1)
        if len(value)>100 or int(expiry)<=time.time():return False
        return secrets.compare_digest(value.encode(),signed_session(int(expiry)).encode())
    except (ValueError,TypeError):return False

def auth(request:Request):
    bearer=request.headers.get('authorization','')
    if secrets.compare_digest(bearer.encode(),('Bearer '+os.environ['APP_TOKEN']).encode()):return
    if valid_session(request.cookies.get(COOKIE,'')):
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin=public_origin() or str(request.base_url).rstrip('/')
            if request.headers.get('origin')!=origin:raise HTTPException(403,'Same-origin browser action required')
        return
    raise HTTPException(401,'Open your private access link again or enter your local access token')
