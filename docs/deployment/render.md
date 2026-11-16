# Render deployment

## Current production resources

- Workspace: `Vitnetwork`
- Web service: `vit` — <https://vit-fwjz.onrender.com>
- Render service ID: `srv-dbtclgu7bikc73do0ov0`
- PostgreSQL: `vitnetwork` (Virginia)
- Key Value / Redis: `vitnetwork-redis` (Virginia)
- Periodic work: in-process schedules plus GitHub Actions; no paid Render worker

`render.yaml` describes these resource names and region. Frontend service URLs
are baked into the Docker image at build time using the defaults in `Dockerfile`.
The Render deploy workflow uses Render auto-deploy on pushes to `main`; its
manual-dispatch and commit-verification steps can use the GitHub secrets below.

## Add Render environment values

1. Open the Render dashboard and select the `Vitnetwork` workspace.
2. Open the `vit` web service and choose **Environment**.
3. Add each value required by an enabled feature, then save. Render restarts or
   redeploys the service after environment changes.
4. Verify `/ping` and `/ready` at <https://vit-fwjz.onrender.com>.

`SECRET_KEY` and `JWT_SECRET_KEY` were already generated and stored by Render.
Do not replace them unless intentionally rotating credentials.

Optional values in `render.yaml` are feature-specific; configure only the
integrations being enabled:

- Data providers: `FOOTBALL_DATA_API_KEY`, `ODDS_API_KEY`
- AI/service authentication: `VIT_AI_API_KEY`, `SERVICE_TOKEN_SECRET`
- Tachyon upload: `VIT_STORAGE_API_KEY`, `SERVICE_TOKEN_SECRET`
- Payments: `PAYSTACK_SECRET_KEY`, `PAYSTACK_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY`
- Email: `RESEND_API_KEY`
- Firebase / Google: `GOOGLE_CLIENT_ID`, `FIREBASE_PROJECT_ID`,
  `FIREBASE_SERVICE_ACCOUNT_JSON`
- Admin bootstrap: `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- VIT Chain / validator: `VIT_TREASURY_PRIVATE_KEY`, `GENESIS_VALIDATOR_KEY`,
  `GENESIS_VALIDATOR_ADDRESS`, `GENESIS_VALIDATORS`
- Peer identity: `P2P_NODE_ID`, `P2P_PUBLIC_KEY`
- Optional Render management from the app: `RENDER_API_KEY`

Use the exact key names above. Copy values from their provider dashboards
directly into Render; never place live values in the repository, workflow YAML,
or issue comments. Generate fresh high-entropy values for application-owned
secrets such as `SERVICE_TOKEN_SECRET`.

## Add GitHub Actions secrets

1. Open the repository on GitHub: **Settings → Secrets and variables → Actions**.
2. Choose **New repository secret** and add:
   - `RENDER_API_KEY` — a Render API key with access to the `Vitnetwork`
     workspace. Used only for manual deploys and commit-specific deployment
     verification.
   - `RENDER_SERVICE_ID` — `srv-dbtclgu7bikc73do0ov0`. Optional because the
     workflow has this service ID as its default.
   - `VIT_STORAGE_API_KEY` and `SERVICE_TOKEN_SECRET` — required to upload
     retrained model artifacts from the scheduled GitHub Action to Tachyon.
     Use the same `SERVICE_TOKEN_SECRET` configured on the Render gateway (and
     Tachyon if its service-auth validation is enabled).
3. Pushes to `main` can deploy through Render auto-deploy without these GitHub
   secrets. The workflow still checks the public `/ready` endpoint.

`keep-alive.yml` and `retrain-cron.yml` do not need Render API credentials.
The staging-only scheduled health workflow instead uses the `staging` GitHub
environment and its `STAGING_GITHUB_SCHEDULER_TOKEN` secret and staging URL
variables. The production scheduled-jobs API is currently restricted to
testing/staging, so that staging token is not a production scheduler token.
