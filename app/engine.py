import asyncio, os, time, logging
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from app import store
from app.mail import poll
class ManualRequired(Exception): pass
class Ineligible(Exception): pass
async def guard(page,a):
    if urlparse(page.url).hostname not in a['allowed_hosts']: raise ManualRequired('Unexpected domain; manual inspection required')
    for s in a['block_selectors']:
        if await page.locator(s).count() and await page.locator(s).first.is_visible():
            raise ManualRequired('CAPTCHA, payment, eligibility or sensitive consent detected')
async def eligibility(page,a):
    await page.goto(a['eligibility_url'])
    if urlparse(page.url).hostname not in a['allowed_hosts']: raise ManualRequired('Unexpected eligibility domain')
    if await page.locator(a['ineligible_selector']).count() and await page.locator(a['ineligible_selector']).first.is_visible():
        raise Ineligible(a.get('ineligible_reason','Platform indicates this account is not eligible'))
    await guard(page,a)
    try:
        await page.locator(a['eligibility_selector']).wait_for(state='visible',timeout=15000)
    except Exception:
        raise ManualRequired('Eligibility could not be confirmed by this adapter; inspect official offer manually')

async def steps(page,a,items,data):
    for s in items:
        await guard(page,a)
        loc=page.locator(s['selector'])
        if s['action']=='fill': await loc.fill(data[s['value']])
        elif s['action']=='click': await loc.click()
        elif s['action']=='check': await loc.check()
        else: await loc.wait_for(state='visible')
        await guard(page,a)
async def run(jid,a,data,mail_poll=poll):
    store.update(jid,status='running'); store.event(jid,'Registration started')
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(executable_path=os.getenv('BROWSER_EXECUTABLE') or None,headless=os.getenv('HEADLESS','false').lower()=='true')
            try:
                ctx=await browser.new_context()
                async def route(r):
                    u=urlparse(r.request.url)
                    if u.scheme in ('http','https') and u.hostname not in a['allowed_hosts']: await r.abort()
                    else: await r.continue_()
                await ctx.route('**/*',route)
                page=await ctx.new_page(); page.set_default_timeout(15000)
                if a['eligibility_timing']=='before_registration':
                    await eligibility(page,a); store.event(jid,'Platform eligibility indicator confirmed before registration')
                else: store.event(jid,'Account-specific eligibility requires login; checked after verification, before activation')
                since=time.time(); await page.goto(a['signup_url'])
                await steps(page,a,a['registration'],data)
                await page.locator(a['registration_success']).wait_for(state='visible'); await guard(page,a)
                store.update(jid,registration='created'); store.event(jid,'Account created; waiting for verification email')
                found=await asyncio.to_thread(mail_poll,data['email'],a,since)
                if a['verification_mode']=='link':
                    link=found['link']
                    if urlparse(link).hostname not in a['verification_hosts']: raise ManualRequired('Verification URL rejected')
                    await page.goto(link)
                else:
                    await steps(page,a,a['otp_steps'],data|{'otp':found['otp']})
                await page.locator(a['verification_success']).wait_for(state='visible'); await guard(page,a)
                store.update(jid,verification='verified'); store.event(jid,'Email verified')
                if a['eligibility_timing']=='after_verification':
                    await eligibility(page,a); store.event(jid,'Platform account eligibility confirmed')
                await page.goto(a['trial_url']); await guard(page,a)
                await page.locator(a['trial_evidence']).wait_for(state='visible')
                if a.get('no_payment_required') is not True:
                    raise ManualRequired('Payment or subscription consent requires manual activation; no automatic resume')
                await steps(page,a,a['activation'],data)
                await page.locator(a['trial_success']).wait_for(state='visible'); await guard(page,a)
                store.update(jid,trial='active',status='completed',activated=store.now()); store.event(jid,'Trial activation confirmed by configured success indicator')
            finally: await browser.close()
    except Ineligible as e:
        store.update(jid,status='ineligible',trial='not_eligible'); store.event(jid,str(e))
    except ManualRequired as e:
        store.update(jid,status='manual_required'); store.event(jid,str(e))
    except asyncio.CancelledError:
        store.update(jid,status='interrupted'); store.event(jid,'Worker stopped; inspect account manually. No retry.')
        raise
    except Exception as e:
        # Never persist exception bodies: they can contain passwords, OTPs or token URLs.
        logging.warning('Job %s failed (%s)',jid,type(e).__name__)
        store.update(jid,status='failed'); store.event(jid,'Process failed: '+type(e).__name__+'. Inspect target manually before any further attempt.')
