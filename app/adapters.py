"""Versioned data-driven adapters. Drafts are editable without source changes."""
import json, re, ipaddress
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
from app import store

def slug_check(name):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',name): raise ValueError('Invalid application ID')
def url_check(value):
    u=urlparse(value)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):raise ValueError('Public HTTPS URL required')
    host=u.hostname.lower()
    if host=='localhost' or host.endswith(('.localhost','.local','.internal')) or '.' not in host:raise ValueError('Local targets are not supported')
    try:
        if not ipaddress.ip_address(host).is_global:raise ValueError('Private targets are not supported')
    except ValueError as e:
        if 'Private' in str(e):raise
    return host

def service_key(a):
    host=urlparse(a['signup_url']).hostname.lower().removeprefix('www.')
    for canonical,roots in {'chatgpt.com':['chatgpt.com','openai.com'],'canva.com':['canva.com'],'capcut.com':['capcut.com','capcut.net'],'alightmotion.com':['alightmotion.com','alightcreative.com']}.items():
        if any(host==root or host.endswith('.'+root) for root in roots):return canonical
    return host
def all_configs():
    configs={}
    for p in Path('adapters').glob('*.json'):
        try: configs[p.stem]=json.loads(p.read_text())
        except (ValueError,OSError):pass
    configs.update(store.app_all());return configs

def get(name):
    slug_check(name)
    a=all_configs().get(name)
    if a is None:raise ValueError('Application not found')
    return a

def validate(a):
    if a.get('policy',{}).get('automation')!='allowed':raise ValueError(a.get('policy',{}).get('reason') or 'Automation permission is unknown or forbidden')
    if a.get('reviewed') is not True:raise ValueError('Workflow has not been reviewed')
    policy=a.get('policy',{})
    if policy.get('automation')!='allowed':raise ValueError(policy.get('reason') or 'Automation permission is unknown or forbidden')
    url_check(policy['source_url'])
    reviewed=date.fromisoformat(policy['reviewed_on']);age=(date.today()-reviewed).days
    if age<0 or age>30:raise ValueError('Policy review expired; review official terms again (30 days)')
    if not policy.get('reason'):raise ValueError('Policy review rationale required')
    if not isinstance(a.get('no_payment_required',False),bool):raise ValueError('no_payment_required must be a boolean')
    for field in ['signup_url','trial_url','terms_url','eligibility_url']:
        host=url_check(a[field])
        if host not in a['allowed_hosts']:raise ValueError('URL host missing from allowed_hosts')
    if a.get('eligibility_timing') not in ['before_registration','after_verification']:raise ValueError('Specify eligibility_timing')
    for field in ['registration_success','verification_success','trial_success','trial_evidence','eligibility_selector','ineligible_selector','block_selectors','registration','activation','senders','verification_hosts','subject_pattern','otp_pattern','verification_mode']:
        if not a.get(field):raise ValueError('Missing adapter field: '+field)
    for host in a['allowed_hosts']:url_check('https://'+host)
    if not set(a['verification_hosts'])<=set(a['allowed_hosts']):raise ValueError('Verification hosts must be allowed')
    if a['verification_mode'] not in ['link','otp']:raise ValueError('Unsupported verification mode')
    if a['verification_mode']=='otp' and not a.get('otp_steps'):raise ValueError('OTP steps required')
    pattern=re.compile(a['otp_pattern']);re.compile(a['subject_pattern'])
    if pattern.groups<1:raise ValueError('OTP regex needs a capture group')
    for items in [a['registration'],a['activation'],a.get('otp_steps',[])]:
        for step in items:
            if step['action'] not in ['fill','click','check','wait']:raise ValueError('Unknown action')
            if not step.get('selector'):raise ValueError('Selector required')
            if step['action']=='fill' and step.get('value') not in ['name','email','password','otp']:raise ValueError('Unknown input field')
            if step['action'] in ['click','check'] and step.get('reviewed_safe') is not True:raise ValueError('Every action requires review')
    return a

def load(name):return validate(get(name))
def summary(name,a):
    try:validate(a);enabled=True;reason='Reviewed adapter; account eligibility checked during process'
    except (ValueError,KeyError,TypeError) as e:enabled=False;reason=str(e)
    return {'id':name,'name':a.get('name',name),'url':a.get('signup_url',''),'enabled':enabled,'reason':reason,'duration':a.get('duration','Unknown'),'terms_url':a.get('terms_url',''),'policy':a.get('policy',{})}
