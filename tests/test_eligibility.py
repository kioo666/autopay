import asyncio
import pytest
from app.engine import eligibility, Ineligible, ManualRequired
class Locator:
    def __init__(self,visible,timeout=False):self.visible=visible;self.timeout=timeout
    @property
    def first(self):return self
    async def count(self):return int(self.visible)
    async def is_visible(self):return self.visible
    async def wait_for(self,**kwargs):
        if self.timeout:raise TimeoutError('secret')
class Page:
    url='https://example.com/offer'
    def __init__(self,ineligible=False,timeout=False):self.ineligible=ineligible;self.timeout=timeout
    async def goto(self,url):pass
    def locator(self,s):return Locator(self.ineligible if s=='[denied]' else False,self.timeout)
def test_eligible():
    a={'eligibility_url':'https://example.com/offer','allowed_hosts':['example.com'],'ineligible_selector':'[denied]','eligibility_selector':'[eligible]','block_selectors':[]}
    asyncio.run(eligibility(Page(),a))
    with pytest.raises(Ineligible):asyncio.run(eligibility(Page(ineligible=True),a))
    with pytest.raises(ManualRequired,match='could not be confirmed'):asyncio.run(eligibility(Page(timeout=True),a))
