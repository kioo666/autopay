"""Account registry, live OAuth health checks, no email rotation on failure."""
import secrets
from app import store, mail

def health(email):
    try:
        api=mail.service(email)
        profile=api.users().getProfile(userId='me').execute()
        api.users().messages().list(userId='me',maxResults=1).execute()
        if profile['emailAddress'].lower()!=email.lower():
            return {'email':email,'usable':False,'reason':'OAuth identity does not match selected mailbox'}
        return {'email':email,'usable':True,'reason':'Gmail API accessible'}
    except Exception as e:
        return {'email':email,'usable':False,'reason':'Reconnect Gmail or check network ('+type(e).__name__+')'}
def select(email=None,random_selection=False):
    available=[a['email'] for a in store.accounts()]
    if not random_selection:
        if not email or email not in available: raise ValueError('Selected Gmail is not connected')
        result=health(email)
        if not result['usable']: raise ValueError(result['reason'])
        return email
    usable=[a for a in available if health(a)['usable']]
    if not usable: raise ValueError('No usable Gmail account; reconnect or check network')
    return secrets.choice(usable)
