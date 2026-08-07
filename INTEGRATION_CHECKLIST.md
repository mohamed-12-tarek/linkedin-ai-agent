# Integration Checklist

This document lists every external account, credential, callback, webhook, and local dependency currently used or planned by the application.

## Required For Local MVP

### Docker Desktop

- Service: Docker Desktop with Linux containers and Compose v2.
- Required: Yes for the supported local run.
- Uses: PostgreSQL, FastAPI, Streamlit, Alembic migration container.
- Obtain: https://www.docker.com/products/docker-desktop/
- Free tier: Yes for personal/small-business use subject to Docker licensing.
- Credentials: None for local images.
- Local requirements: Docker Engine running, at least 4 GB RAM recommended, ports `5432`, `8000`, and `8501` available.

### PostgreSQL

- Service: PostgreSQL 16 Alpine through Docker.
- Required: Yes for the local application.
- Uses: SQLAlchemy data, LangGraph checkpointing, workflow history, publishing history.
- Account: None locally.
- Credentials: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`.
- Do not use repository defaults for these values. Copy `.env.example` to `.env` and set unique local values before running Compose.
- Free tier: Local Docker is free. Supabase Free or Neon Free can replace it later.
- Local requirements: Docker named volume `postgres_data`.

### Local Storage

- Service: Local filesystem storage.
- Required: Yes for uploads and generated images when `STORAGE_BACKEND=local`.
- Uses: `storage/uploads`, `storage/images`, CV files in future phases.
- Credentials: None.
- Configuration: `STORAGE_BACKEND=local`, `LOCAL_STORAGE_PATH=/app/storage`.
- Git rule: Storage contents are ignored and must never be committed.

## AI Text Providers

At least one text provider is required before real AI workflows can run. Phase 3 model records can also provide encrypted per-model keys.

### Groq

- Service: Groq Cloud API.
- Required: Optional provider; required if a registered Groq model is selected.
- Uses: Writer, reviewer, judge, translator, and future workflow nodes.
- Obtain: https://console.groq.com/
- Credentials: `GROQ_API_KEY`, or an encrypted key in the Model Registry.
- Free tier: Yes, subject to current rate and usage limits.
- Permissions: API key access to the selected chat models.
- Callback/webhook: None.

### Google Gemini

- Service: Google AI Studio Gemini API.
- Required: Optional provider; required if a registered Gemini model is selected.
- Uses: Any LLM role.
- Obtain: https://aistudio.google.com/apikey
- Credentials: `GOOGLE_API_KEY`, or an encrypted key in the Model Registry.
- Free tier: Yes, subject to current model quotas and regional availability.
- Permissions: Generative Language API access.
- Callback/webhook: None.

### OpenRouter

- Service: OpenRouter API.
- Required: Optional provider; required if an OpenRouter model is selected.
- Uses: Swappable text models and free-model routing.
- Obtain: https://openrouter.ai/keys
- Credentials: `OPENROUTER_API_KEY`, or an encrypted key in the Model Registry.
- Free tier: Free models are available, subject to model limits and provider availability. Paid credits are not required for free models, but verify the selected model’s pricing.
- Permissions: API key access to selected models.
- Configuration: `OPENROUTER_BASE_URL`, `OPENROUTER_APP_NAME`, `OPENROUTER_SITE_URL`.
- Callback/webhook: None.

## Image Providers

### Pollinations

- Service: Pollinations image generation.
- Required: Optional account; default image provider requires no account or key.
- Uses: AI image mode and image fallback chain.
- Obtain: https://pollinations.ai/
- Credentials: None.
- Free tier: Yes, no API key required by the current adapter.
- Configuration: `POLLINATIONS_BASE_URL`, `POLLINATIONS_MODEL`.
- Callback/webhook: None.

### Hugging Face

- Service: Hugging Face Inference API.
- Required: Optional fallback provider; recommended when Pollinations availability is insufficient.
- Uses: AI image fallback.
- Obtain: https://huggingface.co/settings/tokens
- Credentials: `HUGGINGFACE_API_TOKEN` with inference permission.
- Free tier: A free account/token tier exists subject to current quotas and model availability.
- Configuration: `HUGGINGFACE_IMAGE_MODEL`.
- Callback/webhook: None.

### OpenAI Images

- Service: OpenAI Images API.
- Required: Optional provider only. It is not required for the free-tier default architecture.
- Uses: Optional image fallback.
- Obtain: https://platform.openai.com/api-keys
- Credentials: `OPENAI_API_KEY`.
- Free tier: Do not assume a free quota; billing may be required. Keep it disabled in `IMAGE_PROVIDER_ORDER` unless explicitly approved.
- Configuration: `OPENAI_IMAGE_MODEL`.
- Callback/webhook: None.

## Telegram Human Approval

### Telegram Bot API

- Service: Telegram Bot API.
- Required: Required for Telegram approval and notification workflow; optional for text/image generation tests.
- Uses: Approval messages, inline buttons, callbacks, selected image delivery, action acknowledgements.
- Obtain: Open Telegram, message `@BotFather`, run `/newbot`, and copy the bot token.
- Credentials: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`.
- Free tier: Yes.
- Permissions: The user must start the bot and allow it to send messages in the target chat.
- Webhook: Configure Telegram’s webhook to the public HTTPS URL below, using the same secret token:

```text
https://YOUR_PUBLIC_BACKEND_HOST/api/v1/telegram/webhook
```

- Configuration: `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`.
- Local development: Telegram cannot reach `localhost`; use an HTTPS tunnel such as Cloudflare Tunnel or ngrok, subject to their current free-tier terms.

## LinkedIn OAuth and Publishing

### LinkedIn Developer Application

- Service: LinkedIn Developer Platform.
- Required: Required for real publishing; optional when using `LINKEDIN_DRY_RUN=true`.
- Uses: OAuth connection, profile URN discovery, text posts, image posts.
- Obtain: https://www.linkedin.com/developers/apps
- Credentials: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`.
- Free tier: Developer app registration and API access are generally free, subject to LinkedIn product approval and current policies. Publishing permissions are not guaranteed automatically.
- Required products/permissions: OpenID Connect/profile access for `userinfo`; `w_member_social` for member posting. Use the exact permissions granted to the app by LinkedIn.
- OAuth callback URL:

```text
https://YOUR_PUBLIC_BACKEND_HOST/api/v1/linkedin/oauth/callback
```

- Local callback: `http://localhost:8000/api/v1/linkedin/oauth/callback` can be used for browser-local testing if LinkedIn accepts the exact registered URL.
- Configuration: `LINKEDIN_REDIRECT_URI`, `LINKEDIN_SCOPES`, `LINKEDIN_API_VERSION`, `LINKEDIN_DRY_RUN`.
- Publishing caution: LinkedIn API access, products, scopes, rate limits, and review requirements can change. Confirm current approval requirements in the developer portal before enabling production publishing.

## Optional Storage Providers

### Supabase Storage

- Service: Supabase project and Storage bucket.
- Required: Optional replacement for local storage.
- Uses: Hosted image and document storage.
- Obtain: https://supabase.com/
- Credentials: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`.
- Free tier: Yes, subject to current quotas.
- Permissions: Service-role access must remain backend-only; never expose it to Streamlit/browser code.
- Callback/webhook: None.

### Neon PostgreSQL

- Service: Neon project.
- Required: Optional replacement for local PostgreSQL.
- Uses: Hosted relational database.
- Obtain: https://neon.tech/
- Credentials: Provider connection string placed in `DATABASE_URL`.
- Free tier: Yes, subject to current quotas.
- Callback/webhook: None.

## Future Phase Integrations

### Adzuna

- Service: Adzuna Jobs API.
- Required: Required only for automatic CV job matching; manual jobs work without it.
- Uses: Graph 3 job fetching.
- Obtain: https://developer.adzuna.com/
- Credentials: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`.
- Free tier: Developer free tier with daily limits, subject to current terms.
- Configuration: `ADZUNA_COUNTRY`.
- Callback/webhook: None.

### Public Scheduler Host

- Service: No external account required for local APScheduler.
- Required: Required for periodic job matching and scheduled publishing when those phases are implemented.
- Uses: APScheduler in a continuously running backend/worker process.
- Credentials: None.
- Local requirements: A process that remains alive. Do not run multiple scheduler replicas without a lease/leader-election mechanism.

## Hosting, DNS, TLS, and Frontend Deployment

### Public HTTPS Backend

- Service: A public container host or self-hosted machine with HTTPS.
- Required: Required for production Telegram webhooks and LinkedIn OAuth callbacks; optional for local-only dry-run development.
- Uses: FastAPI, Telegram webhook, LinkedIn OAuth callback, future scheduled jobs.
- Credentials: Host account/deployment token as required by the selected provider; domain/DNS credentials only if using a custom domain.
- Free tier: Provider terms change frequently. Render, Railway, and Fly.io must be checked at signup for current no-card and free-tier availability before selection. No provider requiring a card is mandatory for this project.
- Required configuration: Public `FRONTEND_URL`, `CORS_ORIGINS`, `BACKEND_URL`, `LINKEDIN_REDIRECT_URI`, and `TELEGRAM_WEBHOOK_URL`.
- TLS: Use a provider-managed certificate or free Let's Encrypt certificate. Never commit certificate private keys.
- Runtime: Must support a persistent container, PostgreSQL connectivity, writable/persistent storage or external object storage, and outbound HTTPS.

### HTTPS Tunnel For Local Webhooks

- Service: Cloudflare Tunnel or another no-card HTTPS tunnel.
- Required: Optional for local Telegram webhook/LinkedIn callback testing.
- Obtain: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Credentials: A tunnel token may be required for named/persistent tunnels. Store it only in `.env` or the process environment.
- Free tier: Cloudflare Tunnel has a free offering subject to current terms.
- Callback URLs: Set Telegram and LinkedIn callbacks to the generated HTTPS hostname.
- Local requirement: The tunnel process must remain running alongside Docker Compose.

### Streamlit Community Cloud

- Service: Streamlit Community Cloud.
- Required: Optional hosted Phase 1 frontend.
- Uses: Streamlit UI connecting to the public FastAPI backend.
- Obtain: https://share.streamlit.io/
- Credentials: GitHub account/repository access. Configure `BACKEND_URL` using Streamlit secrets or deployment environment, never in source.
- Free tier: Community Cloud is free subject to current limits.
- Permissions: Repository read access for deployment.
- Callback/webhook: None.

### GitHub

- Service: GitHub repository and Actions.
- Required: Optional for local operation; recommended for collaboration and automated secret scanning.
- Credentials: Developer Git credentials or GitHub CLI authentication. CI needs no application secrets for the current security scan.
- Free tier: Public repositories and limited private-repository Actions are available subject to current limits.
- Security: Enable branch protection and secret scanning where available. Never store runtime credentials in repository variables; use encrypted Actions secrets only for deployment jobs that actually require them.

## Local Runtime and OS Requirements

- Operating systems: Windows with Docker Desktop/WSL2, macOS with Docker Desktop, or Linux with Docker Engine and Compose v2.
- CPU/RAM: 2 CPU cores and 4 GB available RAM minimum recommended; image/LLM operations may need more.
- Ports: `5432` PostgreSQL, `8000` FastAPI, and `8501` Streamlit must be available or remapped in Compose.
- Docker volume: `postgres_data` persists relational and LangGraph checkpoint data.
- Bind mount: `./storage:/app/storage` persists uploads and generated images.
- Directories: `storage/uploads`, `storage/images`, and future CV storage are created by the application. The repository tracks only `storage/.gitkeep`.
- Certificates: None required for local HTTP. Public deployments require TLS; use provider-managed or Let's Encrypt certificates and keep private keys outside Git.
- OS packages: No host Python or native packages are required for the Docker path. Images contain Python 3.12, PostgreSQL client support, Pillow, PDFPlumber, and python-docx dependencies.
- Optional developer tooling: Python 3.12+ is needed only for host-side tests, `pre-commit`, and `detect-secrets`. Install `pre-commit` and `detect-secrets==1.5.0` before enabling the local Git hook.
- Docker images/network access: First build requires access to Docker Hub and Python package indexes.
- Background processes: Current API and Streamlit run as Compose services. No separate Celery/Redis worker is required.
- LangGraph checkpointing: Runs in PostgreSQL and creates its own `checkpoint_*` tables at backend startup.
- Migrations: The one-shot `migrations` Compose service must finish successfully before the backend starts.
- Scheduler: APScheduler settings exist, but scheduled publishing/job matching is not implemented yet. When implemented, run exactly one scheduler leader or add a database-backed lease.
- Backups: Back up `postgres_data` and `storage/` together. Database-only backups do not contain image/CV files.
- Time zone: Set `SCHEDULER_TIMEZONE`; containers otherwise use UTC.

## Integration Implementation Status

- Implemented: Groq, Gemini, OpenRouter model adapters; Pollinations, Hugging Face, OpenAI image adapters; Telegram approval; LinkedIn OAuth/publishing; local PostgreSQL/storage.
- Configured but not implemented: Supabase Storage backend, authentication registration/login, APScheduler jobs.
- Planned: Adzuna fetching and CV job matching, profile optimizer workflow, Streamlit feature pages.
- Do not create credentials for configured-but-unimplemented services unless preparing their phase.

## Authentication and Encryption

### Current Authentication Boundary

- Status: Not production-ready yet.
- Current behavior: protected development endpoints use the temporary `X-User-ID` header and verify that the user exists.
- JWT settings are present for OAuth state and future authentication, but user registration/login and bearer-token enforcement are not implemented yet.
- Do not expose the current `X-User-ID` boundary to an internet-facing deployment.
- The authentication phase must implement `/auth/register`, `/auth/login`, JWT bearer validation, password policy, rate limiting, and ownership enforcement before SaaS deployment.

### JWT and Fernet

- Service: Local cryptography; no external account.
- Required: Yes for production authentication and encrypted provider tokens.
- Credentials: `JWT_SECRET_KEY`, `ENCRYPTION_KEY`.
- Generate locally:

```text
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- Requirements: Production/staging reject placeholder JWT and invalid Fernet keys.
- Rotation: Plan a key rotation/migration process before rotating `ENCRYPTION_KEY`; existing encrypted provider tokens depend on it.

## Clone-to-Run Checklist

1. Install Docker Desktop with Linux containers.
2. Clone the repository.
3. Copy `.env.example` to `.env`.
4. Generate local `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, and database password.
5. Build `DATABASE_URL` from the chosen database user, password, host, port, and database name. For Compose, the hostname is `db`.
6. Run `docker compose up -d`.
7. Confirm `docker compose ps` reports database, backend, and frontend healthy.
8. Use `http://localhost:8000/docs` and `http://localhost:8501`.
9. Add provider keys only when using those providers.
10. Configure Telegram and LinkedIn only when those integrations are being tested.

## Complete Environment Variable Inventory

### Application and Network

- `APP_NAME`: Display/API title. Local default is acceptable.
- `APP_ENV`: `development`, `staging`, or `production`. Staging/production enforce secure cryptographic values.
- `APP_DEBUG`: Disable in production.
- `APP_HOST`, `APP_PORT`: FastAPI bind address and port.
- `API_V1_PREFIX`: Backend API prefix, currently `/api/v1`.
- `BACKEND_URL`: Public/backend URL for frontend and callback-aware deployments.
- `FRONTEND_URL`: Public Streamlit URL.
- `CORS_ORIGINS`: Comma-separated allowed browser origins. Set exact HTTPS origins in production; do not use `*` with credentials.
- `LOG_LEVEL`: Application log level. Never log tokens, authorization headers, callback payload secrets, or CV contents.

### Database

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`: Local PostgreSQL container settings.
- `DATABASE_URL`: SQLAlchemy/psycopg connection URL. Required by backend and migration services.

### Authentication and Encryption

- `JWT_SECRET_KEY`: Required by Compose; generate at least 32 random bytes. Used for OAuth state and future JWT authentication.
- `JWT_ALGORITHM`: Current default `HS256`.
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Future auth token lifetimes.
- `ENCRYPTION_KEY`: Required by Compose; a Fernet key used to encrypt provider and LinkedIn tokens in PostgreSQL.

### Storage

- `STORAGE_BACKEND`: Currently only `local` is implemented.
- `LOCAL_STORAGE_PATH`: Container path for uploads/generated files.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`: Reserved for the optional Supabase Storage implementation; currently not active.

### LLM Providers and Assignments

- `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`: Provider-level fallback keys.
- `OPENROUTER_BASE_URL`, `OPENROUTER_APP_NAME`, `OPENROUTER_SITE_URL`: OpenRouter routing/attribution settings.
- `DEFAULT_WRITER_MODEL`, `DEFAULT_REVIEWER_MODEL`, `DEFAULT_JUDGE_MODEL`, `DEFAULT_TRANSLATION_MODEL`: Initial placeholders; role assignment is currently database-managed through Model Registry/user settings.
- Database setup: Register available models and assign Writer, Reviewer, Judge, and Translator roles before Graph 1 can execute. Image prompt generation also uses the Writer role.

### Image Providers

- `POLLINATIONS_BASE_URL`, `POLLINATIONS_MODEL`: Free default image provider.
- `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_IMAGE_MODEL`: Optional free-tier fallback.
- `OPENAI_API_KEY`, `OPENAI_IMAGE_MODEL`: Optional paid-capable fallback; not required.
- `IMAGE_PROVIDER_ORDER`: Comma-separated fallback order. Remove `openai` if paid providers are prohibited for a deployment.
- `MAX_IMAGE_UPLOAD_MB`: Server-side upload limit.

### Telegram

- `TELEGRAM_BOT_TOKEN`: BotFather-issued bot token.
- `TELEGRAM_CHAT_ID`: Authorized target chat ID.
- `TELEGRAM_WEBHOOK_URL`: Public HTTPS webhook URL for operational setup tooling.
- `TELEGRAM_WEBHOOK_SECRET`: Random Telegram secret-token value; send it when registering the webhook and keep it private.

### LinkedIn and Publishing

- `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`: LinkedIn application OAuth credentials.
- `LINKEDIN_REDIRECT_URI`: Exact registered OAuth callback URL.
- `LINKEDIN_SCOPES`: Comma-separated granted scopes, currently `openid,profile,w_member_social`.
- `LINKEDIN_API_VERSION`: LinkedIn REST API version header. Review periodically because LinkedIn versions expire.
- `LINKEDIN_DRY_RUN`: Avoid real publishing while preserving history/idempotency behavior.
- `PUBLISHER_MAX_RETRIES`, `PUBLISHER_RETRY_DELAY_SECONDS`: Retry controls for transient network, `429`, and `5xx` responses.

### Jobs and Scheduling

- `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ADZUNA_COUNTRY`: Future Graph 3 integration; not currently active.
- `SCHEDULER_ENABLED`, `SCHEDULER_TIMEZONE`: Future APScheduler execution controls; scheduler jobs are not currently registered.
