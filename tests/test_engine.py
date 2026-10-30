import asyncio, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as _p:
    _browser_path=os.getenv('BROWSER_EXECUTABLE') or _p.chromium.executable_path
pytestmark=pytest.mark.skipif(not Path(_browser_path).exists(),reason='Chromium unavailable; run python -m playwright install chromium')
from app import store
from app.engine import run
from tests.test_core import env
class Fixture(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        pages={
          '/signup':'<input name="name"><input type="email"><input type="password"><button onclick="document.body.innerHTML=\'<b data-created>created</b>\'">Register</button>',
          '/verify':'<b data-verified>verified</b>',
          '/trial':'<b data-eligible>7 day free trial</b><button onclick="document.body.innerHTML=\'<b data-active>active</b>\'">Start trial</button>',
          '/payment':'<b data-eligible>Trial</b><input autocomplete="cc-number">',
          '/captcha':'<iframe src="/challenge" title="captcha"></iframe>'}
        self.send_response(200); self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(pages.get(self.path,'').encode())
@pytest.fixture
def fixture_server():
    s=ThreadingHTTPServer(('127.0.0.1',0),Fixture);t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    yield 'http://127.0.0.1:'+str(s.server_port)
    s.shutdown();s.server_close()
def adapter(base):
    return {'eligibility_timing':'after_verification','eligibility_url':base+'/trial','eligibility_selector':'[data-eligible]','ineligible_selector':'[data-ineligible]','signup_url':base+'/signup','trial_url':base+'/trial','allowed_hosts':['127.0.0.1'],'verification_hosts':['127.0.0.1'],'verification_mode':'link','no_payment_required':True,'block_selectors':['input[autocomplete="cc-number"]','iframe[title="captcha"]'],'registration':[{'action':'fill','selector':'input[name=name]','value':'name'},{'action':'fill','selector':'input[type=email]','value':'email'},{'action':'fill','selector':'input[type=password]','value':'password'},{'action':'click','selector':'button'}],'registration_success':'[data-created]','verification_success':'[data-verified]','trial_evidence':'[data-eligible]','activation':[{'action':'click','selector':'button'}],'trial_success':'[data-active]'}
@pytest.mark.parametrize('mode',['success','payment','captcha','consent','mail_error'])
def test_engine(fixture_server,monkeypatch,mode):
    monkeypatch.setenv('HEADLESS','true');a=adapter(fixture_server)
    if mode=='payment':a['trial_url']=fixture_server+'/payment'
    if mode=='captcha':a['signup_url']=fixture_server+'/captcha'
    if mode=='consent':a['no_payment_required']=False
    j=store.create('fixture','owner@example.com','7 days')
    def mail(*args):
        if mode=='mail_error':raise TimeoutError('secret-token-must-not-leak')
        return {'link':fixture_server+'/verify'}
    asyncio.run(run(j,a,{'name':'Real Owner','email':'owner@example.com','password':'private-password'},mail_poll=mail))
    result=store.jobs()[0]
    assert result['status']==('completed' if mode=='success' else 'failed' if mode=='mail_error' else 'manual_required')
    assert (result['trial']=='active')==(mode=='success')
    assert 'private-password' not in str(result) and 'secret-token-must-not-leak' not in str(result)
