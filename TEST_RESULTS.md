# TrialFlow 2.0 — Verification Results

Environment: Python 3.12.14. Executed 30 October 2026.

## Automated tests

`python -m pytest -q`: **30 passed, 5 skipped**, 1 upstream FastAPI/Starlette TestClient deprecation warning.

Passed coverage:

- Encrypted secret storage round trip, plaintext absence, history persistence, duplicate constraints.
- MIME parsing, OTP extraction, trusted-host verification URL extraction, ambiguous/untrusted link rejection.
- Gmail message matching by recipient, sender and timestamp; no secret leakage in health errors.
- Manual and random email selection; random excludes inaccessible accounts; no usable account prevents start and does not reserve a claim.
- Live-health logic for OAuth identity mismatch and API failures (Google API mocked, not a real account).
- Gmail removal, active-job protection, history preservation, explicit local-only removal semantics.
- OAuth PKCE request, state expiry/replay rejection, callback denial, encrypted token registry write, callback query redaction (Google OAuth mocked).
- Application create/read/update/delete; unreviewed/forbidden/unknown/expired-review blocks; public HTTPS validation; strict payment booleans and reviewed actions.
- API bearer authentication, restart interruption, eligibility confirmation requirement.
- Atomic cross-email service reservation, known service aliases, immutable application history, selected mailbox passed to worker.
- Eligibility indicator handling: eligible, not eligible, unknown; unexpected-domain and sensitive-element guards (page fixture).
- Four named platform presets remain stopped and include reasons.

## Real process smoke checks

Started Uvicorn as a separate process with a temporary database and test-only secrets. Verified over HTTP:

- Dashboard served and contains Gmail Manager.
- Authenticated Gmail registry endpoint returned expected empty list.
- Presets listed with disabled status.
- New application created as draft and returned in list.
- Graceful server shutdown.

Dashboard JavaScript passed `node --check`. Python modules passed `compileall`.

## Not verified

Five Playwright browser end-to-end scenarios are included but skipped because Chromium is not installed: success, payment guard, CAPTCHA guard, sensitive consent, mail timeout. Full Chromium download failed previously; headless-shell download was also attempted during this revision and failed with an invalid/truncated archive. No substitute browser verification is claimed.

Real Gmail OAuth consent, refresh, mailbox reading and real production registration/trial activation have **not** been exercised. OAuth/API tests use fixtures. No account was created, no email sent, no trial claimed, and no payment made.

Visual browser QA is not completed. Dynamic application support requires a valid reviewed workflow; no production trial adapter is enabled by default. Install Chromium locally and run the full test suite before reviewing/testing a real adapter on an eligible owned account.

## Hosted preparation revision 2.1

Latest run: **34 passed, 5 skipped**, same upstream deprecation warning. Added tests for hosted HTTPS callback derivation, OAuth Web client validation, rejection of untrusted OAuth endpoints, hosted configuration checks, signed cookie expiry and cross-origin mutation rejection.

Real local Uvicorn HTTP smoke passed for `/healthz`, bearer-to-HttpOnly-session exchange, and subsequent authenticated registry access without a bearer header. Dashboard JS syntax and Python compilation passed.

Dockerfile and Railway configuration are prepared, not built or deployed. Railway connection is still unconfirmed; no Railway tools were available at handoff. No Google OAuth Web client credentials are configured. Existing Ocean Store Vercel resources were read-only inspected, not changed. No hosted URL, browser end-to-end success or real Gmail connection is claimed.


## Verifikasi lanjutan 31 Oktober 2026
37 tes lulus, 5 tes browser dilewati (Chromium belum terpasang). Ditambahkan endpoint kesiapan berautentikasi, indikator dashboard, launcher lokal, dan tes kerahasiaan respons kesiapan. OAuth Gmail dan aktivasi trial produksi belum diuji.
