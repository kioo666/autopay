import time, base64
import pytest
from app import mail
from tests.test_core import env
class Call:
    def __init__(self,value):self.value=value
    def execute(self):return self.value
class Gmail:
    def __init__(self,m):self.m=m
    def users(self):return self
    def messages(self):return self
    def list(self,**kwargs):return Call({'messages':[{'id':'x'}]})
    def get(self,**kwargs):return Call(self.m)
def message(sender='verify@safe.test',recipient='owner@example.com',timestamp=None):
    return {'internalDate':str(int((timestamp or time.time())*1000)),'payload':{'mimeType':'text/plain','headers':[{'name':'From','value':sender},{'name':'To','value':recipient},{'name':'Subject','value':'Verify your email'}],'body':{'data':base64.urlsafe_b64encode(b'OTP: 123456').decode()}}}
@pytest.mark.parametrize('case',['valid','sender','recipient','old'])
def test_matching(monkeypatch,case):
    m=message(sender='evil@safe.test' if case=='sender' else 'verify@safe.test',recipient='other@example.com' if case=='recipient' else 'owner@example.com',timestamp=time.time()-600 if case=='old' else None)
    monkeypatch.setattr(mail,'service',lambda email:Gmail(m))
    clock=iter([0,0,2]);monkeypatch.setattr(mail.time,'monotonic',lambda:next(clock));monkeypatch.setattr(mail.time,'sleep',lambda _:None)
    a={'senders':['verify@safe.test'],'subject_pattern':'verify','otp_pattern':r'OTP: (\d{6})','verification_hosts':['safe.test'],'verification_mode':'otp'}
    if case=='valid':assert mail.poll('owner@example.com',a,time.time()-10,timeout=1)['otp']=='123456'
    else:
        with pytest.raises(TimeoutError):mail.poll('owner@example.com',a,time.time()-10,timeout=1)
