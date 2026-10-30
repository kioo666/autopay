import base64, json, re, html, time
from urllib.parse import urlparse
from email.utils import parseaddr, getaddresses
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from app.store import secret_get, secret_set
SCOPES=['https://www.googleapis.com/auth/gmail.readonly']
def service(email):
    raw=secret_get('gmail:'+email)
    if not raw: raise ValueError('Connect Gmail first')
    creds=Credentials.from_authorized_user_info(json.loads(raw),SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request()); secret_set('gmail:'+email,creds.to_json())
    return build('gmail','v1',credentials=creds,cache_discovery=False)
def body(payload):
    out=[]
    def walk(p):
        if p.get('mimeType') in ('text/plain','text/html') and p.get('body',{}).get('data'):
            out.append(base64.urlsafe_b64decode(p['body']['data']).decode(errors='replace'))
        for sub in p.get('parts',[]): walk(sub)
    walk(payload); return '\n'.join(out)
def extract(text,hosts,pattern):
    links=[html.unescape(x) for x in re.findall(r'https://[^\s<>"\x27]+',text)]
    links=[x for x in links if urlparse(x).hostname in hosts and not urlparse(x).username]
    otp=re.search(pattern,html.unescape(re.sub('<[^>]+>',' ',text)))
    return {'link':links[0] if len(set(links))==1 else None,'otp':otp.group(1) if otp else None}
def poll(email,adapter,since,timeout=120):
    api=service(email); end=time.monotonic()+timeout
    while time.monotonic()<end:
        result=api.users().messages().list(userId='me',q=f'after:{int(since)}',maxResults=30).execute()
        for item in result.get('messages',[]):
            m=api.users().messages().get(userId='me',id=item['id'],format='full').execute()
            if int(m.get('internalDate','0')) < since*1000: continue
            headers={h['name'].lower():h['value'] for h in m['payload'].get('headers',[])}
            if parseaddr(headers.get('from',''))[1].lower() not in adapter['senders']: continue
            recipients=[a.lower() for _,a in getaddresses([headers.get('to',''),headers.get('delivered-to','')])]
            if email.lower() not in recipients: continue
            if not re.search(adapter['subject_pattern'],headers.get('subject',''),re.I): continue
            found=extract(body(m['payload']),adapter['verification_hosts'],adapter['otp_pattern'])
            if found.get(adapter['verification_mode']): return found
        time.sleep(3)
    raise TimeoutError('Verification email not received within timeout')
