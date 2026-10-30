import asyncio
import pytest
from app.engine import guard, ManualRequired
class Locator:
    def __init__(self,visible):self.visible=visible
    @property
    def first(self):return self
    async def count(self):return 1
    async def is_visible(self):return self.visible
class Page:
    def __init__(self,url,visible):self.url=url;self.visible=visible
    def locator(self,s):return Locator(self.visible)
@pytest.mark.parametrize('url,visible,blocked',[('https://safe.test/start',False,False),('https://safe.test.evil/start',False,True),('https://safe.test/payment',True,True)])
def test_guard(url,visible,blocked):
    a={'allowed_hosts':['safe.test'],'block_selectors':['[payment]']}
    if blocked:
        with pytest.raises(ManualRequired):asyncio.run(guard(Page(url,visible),a))
    else:asyncio.run(guard(Page(url,visible),a))
