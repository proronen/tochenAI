### TochenAI – Project Understanding (Draft)

This document summarizes my current understanding of the repository so we can align on vision, scope, and next steps. Please review and annotate directly in this file; I will incorporate your corrections.

## What this project is

- **Goal**: A full‑stack web app that helps users generate, plan, and publish social media content using LLMs, with posting integrations for Facebook, Instagram, and TikTok. 
- **Foundation**: Based on the official Full Stack FastAPI Template (FastAPI + SQLModel + React + Chakra UI), extended with:
  - LLM endpoints (OpenAI, Anthropic, Gemini) for generating content, post ideas, hashtags, and images.
  - Social posting endpoints (Facebook, Instagram, TikTok).
  - User quotas and usage tracking for LLM calls.
  - Data models for scheduled posts and connected social accounts.

## Core capabilities

- **Authentication & Users**
  - JWT auth, password reset via email, first superuser bootstrap, secure password hashing.
  - User profile fields relevant to content generation: `business_description`, `client_avatars`.
  - Quota fields: `quota` and `usage_count` to enforce/track LLM usage.

- **LLM features (backend/app/api/routes/llm.py)**
  - Generate generic content with provider selection: OpenAI, Anthropic, Gemini.
  - Generate post ideas from business context and target audience.
  - Generate full post content (post text + image description) from a selected idea, platform, and tone.
  - Generate platform‑aware hashtags.
  - Generate images via an image generation client (DALL‑E‑style), with size and quality options.
  - Tracks token usage and cost via `LLMUsage` model; quota enforcement implied via client wrappers.

- **Social posting integrations**
  - Facebook: `POST /api/facebook/post` to post a message to a Page using `FACEBOOK_PAGE_ACCESS_TOKEN` and `FACEBOOK_PAGE_ID`.
  - Instagram: `POST /api/instagram/post` to post an image with caption using `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_PAGE_ID`.
  - TikTok: `POST /api/tiktok/post` to upload a video with description using `TIKTOK_ACCESS_TOKEN` and `TIKTOK_USER_ID`.
  - Clients are provided via utilities in `backend/app/utils.py` (e.g., `FacebookClient`, `InstagramClient`, `TikTokClient`).

- **Scheduling & accounts (models)**
  - `UpcomingPost`: stores scheduled post data (media URL, text, hashtags, scheduled time, platform flags, owner linkage, timestamps).
  - `SocialAccount`: stores connected social account credentials/metadata per user (tokens, expiry, account ID/name, platform).
  - `LLMUsage`: stores request/provider/model, token counts, costs, status, and error messages for analytics and quotas.

- **Frontend**
  - React + TypeScript (Vite) with Chakra UI and dark mode.
  - Auto‑generated API client from OpenAPI (`frontend/src/client/*`).
  - Auth flows (login, signup, recover/reset password) and user settings screens.
  - Admin user management and sample Items pages from the template.
  - Playwright E2E tests for auth and user settings.

- **DevOps / Tooling**
  - Docker Compose for local and production; Traefik for reverse proxy/HTTPS guidance.
  - Tests with Pytest (backend) and Playwright (frontend), coverage artifacts in `htmlcov`.
  - Alembic migrations for SQLModel models; revision history included.
  - CI/CD guidance via GitHub Actions (based on template).

## Architecture at a glance

- **Backend**: FastAPI app under `backend/app`, modular routes under `backend/app/api/routes`. Database via SQLModel + PostgreSQL. Alembic for migrations. Security with JWT.
- **Frontend**: React app under `frontend/`, Chakra UI components, OpenAPI‑generated client, route tree under `src/routes`.
- **Contracts**: `frontend/openapi.json` and `openapi-ts.config.ts` drive client generation. The LLM and social posting endpoints are exposed under `/api/`.

## Data models (selected)

- `User`: email, hashed_password, role flags, quota/usage, `business_description`, `client_avatars`.
- `UpcomingPost`: media_url, text, hashtags, scheduled_time, platform toggles, owner and timestamps.
- `SocialAccount`: per‑user platform credentials (access/refresh tokens, expiry, ids/names).
- `LLMUsage`: provider/model, token counts, cost, request_type, success/error, user linkage, timestamps.
- `Item`: template example entity linked to a user (kept from template for demo/admin screens).

## Key endpoints (selected)

- `/api/llm/generate-content` – provider/model‑selectable generic content generation.
- `/api/llm/generate-post-ideas` – context‑aware ideas list output.
- `/api/llm/generate-post-content` – post text + image description from an idea.
- `/api/llm/generate-post` – single post content optimized by platform/tone.
- `/api/llm/generate-hashtags` – platform‑aware hashtags list.
- `/api/llm/providers` – advertised providers + default models.
- `/api/llm/generate-image` – image generation (size/quality).
- `/api/facebook/post`, `/api/instagram/post`, `/api/tiktok/post` – direct posting to platforms.

## Security & configuration

- Secrets via environment variables (`SECRET_KEY`, SMTP, DB, OAuth tokens for platforms). Do not commit tokens.
- Social tokens may expire; refresh logic likely needed (scaffolded by `SocialAccount`).
- Quotas enforced via LLM client wrappers and `usage_count` fields; `LLMUsage` provides auditable logs and cost metrics.

## Assumptions to confirm

1. The vision is a “social content co‑pilot”: generate ideas, produce posts/captions/images, schedule, and publish across platforms within quotas.
2. Scheduling: future work will add background workers/cron to dispatch `UpcomingPost` at `scheduled_time` to selected platforms.
3. Social tokens lifecycle: app will implement OAuth flows and automatic refresh to populate `SocialAccount` and keep tokens valid.
4. Billing/limits: quotas are per‑user and reset monthly (or admin‑managed). Costs tracked by `LLMUsage` inform admin dashboards.
5. Frontend will surface flows for: creating ideas, selecting an idea, generating post text/image brief, saving as `UpcomingPost`, and publishing.
6. Image generation provider is OpenAI DALL‑E (or equivalent) and URLs are returned/stored short‑term; long‑term storage is out of scope.

If any of these assumptions are off, please edit in place and I will realign.

## Open questions

- Do we need multi‑tenant orgs/teams or is it strictly single‑tenant per user?
- Preferred LLM defaults by feature (e.g., Gemini for ideation, OpenAI for polishing)?
- Required compliance constraints (data residency, PII handling, logging retention)?
- Exact schedule dispatch mechanism (in‑app scheduler, Celery/RQ, external cron, or platform webhooks)?
- Content moderation or safety filters before posting?

## Next steps I propose (pending your confirmation)

- Add OAuth flows for Facebook/Instagram/TikTok to populate `SocialAccount` securely; implement token refresh.
- Implement scheduling worker to publish `UpcomingPost` at `scheduled_time` with retries and per‑platform status logging.
- Frontend flows to manage post ideas → content → assets → schedule/publish; add previews per platform.
- Admin dashboards for quota management and `LLMUsage` cost analytics.
- Observability: structured logs and basic metrics for LLM usage and posting success/failures.

— End of draft —


