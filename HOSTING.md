# Hosted deployment handoff — TrialFlow 2.1

Status: deployment files and hosted OAuth/session support prepared. **No hosted server or Google OAuth client has been provisioned in this session.** Railway connection is pending. Existing Ocean Store Vercel project was inspected read-only and is not modified.

## What the deployment agent must do after hosting connection

1. Use the Railway connection to create a dedicated TrialFlow service from this source; do not reuse Ocean Store. Build using Dockerfile, one replica, health check `/healthz`.
2. Attach a persistent volume at `/data`. The startup script sets private directory ownership and drops root before serving requests. Do not launch multiple replicas/workers against this SQLite file.
3. Generate a Fernet key and a 32+ character cryptographically random access token once; store as hosting secrets `MASTER_KEY` and `APP_TOKEN`. Never put either into committed source, logs, or Library artifacts. Preserve both on every redeploy.
4. Generate the service domain, set `PUBLIC_BASE_URL=https://<domain>` and `DATA_DIR=/data`, `HEADLESS=true`. `PORT` is supplied by Railway. Hosted startup requires HTTPS public origin and persistent-path configuration. The configured hostname and Railway's health-check host are allowed; arbitrary Host headers are rejected.
5. Configure a Google Cloud OAuth client of type Web application for the owner's authorized project. Enable Gmail API, add the owner/test accounts to the consent audience if the client is in Testing, and register exactly `https://<domain>/oauth/callback`. The app cannot manufacture client credentials; access to the owner's Cloud project or already-created client config is required.
6. Put the client JSON in the hosting secret `GOOGLE_CLIENT_JSON` (not source). Official authorization/token endpoints are validated. Hosted mode rejects Desktop-only client config. OAuth callback uses configured origin, not request Host, and PKCE + expiring single-use state. Only Gmail read-only scope is requested.
7. Deploy and verify health endpoint, cookie auth, expected stopped presets and manager operations over the actual hosted domain. Verify browser install and the end-to-end fixture suite inside the deployment image. The image has not been built or launched in this environment.
8. Provide the owner a private access link `https://<domain>/#access=<APP_TOKEN>` through the private conversation, never a public page or artifact. This is a bearer credential: anyone with the full link can access the workspace. The fragment is consumed in the browser, removed from the address bar and exchanged for an HttpOnly, Secure, SameSite=Strict session, valid 12 hours. It is not sent in HTTP request paths. Do not include the token in server query parameters.
9. The owner opens the private link, then approves Gmail authorization at Google. No source editing, terminal commands, Google password sharing or token copying is required for their normal use. The private link is needed again when the session expires. Google can require consent again if tokens expire/revoke.

## Remaining external prerequisites

- Railway account connection/authorization is not yet confirmed. Do not claim deployment is live until verified.
- Google OAuth Web client configuration and its authorized Cloud project have not been provided or connected. A Gmail connection inside ChatGPT alone does not supply a standalone application's OAuth client or transferable credentials.
- The four named production platform presets remain stopped for their documented reasons; hosting the app does not make those workflows supported. An authorized real adapter must be reviewed/tested separately before enabling a real claim.
- Hosting charges, if required by the chosen plan, must be disclosed before purchasing a plan. No paid plan or subscription has been activated.

## Files

`Dockerfile`, `.dockerignore`, `railway.toml`, `start_hosted.py`, `app/config.py`, `app/access.py`, HTTPS OAuth handling, `/healthz`, and hosting/session unit tests.

## Verification in this session

Unit/API tests and local HTTP smoke tests are separate from deployment, Google consent, browser integration and real platform activation. See TEST_RESULTS.md. No hosted link exists yet.
