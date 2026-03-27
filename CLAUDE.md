# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ShadowBroker is a real-time OSINT dashboard. A **Python/FastAPI backend** aggregates 19 live data feeds and 7 static reference datasets, and a **Next.js 16 frontend** renders them on a MapLibre GL map with a military-styled HUD. It also includes an AI assistant for natural-language queries against live dashboard data and a radio scanner integration.

## Commands

### Local Dev (starts both frontend and backend)
```bash
cd frontend && npm run dev
```
This runs Next.js on :3000 and uvicorn on :8000 concurrently via `start-backend.js`.

### Frontend Only
```bash
cd frontend
npm run dev:frontend     # dev server
npm run build            # production build
npm run lint             # eslint
npm run test             # vitest (single run)
npm run test:watch       # vitest watch mode
npx vitest run src/__tests__/utils/positioning.test.ts  # single test file
```

### Backend Only
```bash
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload          # dev with hot reload
python -m pytest tests/ -v --tb=short        # all tests
python -m pytest tests/test_api_smoke.py -v  # single test file
python -m pytest tests/test_api_smoke.py::TestHealthEndpoint::test_health_returns_200 -v  # single test
```

### Starter Script
```bash
./start.sh           # discovers Node.js, validates env, starts both servers
./start.sh --check   # setup-only mode (no server launch, just validates env + node)
```
Searches nvm > fnm > volta > brew > system PATH for Node >= 18. Caches the working path to `.node-path` for subsequent runs.

### Docker
```bash
./compose.sh up -d            # auto-detects docker/podman
docker compose up -d --build  # rebuild
```

## Architecture

### Backend Data Flow

`backend/main.py` is the FastAPI app. On startup (lifespan handler), it:
1. Validates env vars (`services/env_check.py`)
2. Loads static reference data (airports, datacenters, military bases, power plants)
3. Starts AIS WebSocket stream for real-time ship data (`services/ais_stream.py` -> `ais_proxy.js`)
4. Starts US Navy carrier OSINT tracker (`services/carrier_tracker.py`, refreshes every 12h)
5. Starts APScheduler with tiered fetchers:
   - **Fast** (60s): flights, military flights, ships, satellites
   - **Slow** (5min): news, earthquakes, fires, defense stocks, oil, weather, space weather, internet outages, CCTV, KiwiSDR, frontlines, GDELT
   - **Very slow** (15min): GDELT (reinforcement), LiveUAMap (Playwright scrape)
   - **CCTV ingest** (10min): runs 9 camera ingestors (TFL, LTA Singapore, Austin, NYC DOT, Spain DGT, Madrid, Malaga, Vigo, Vitoria-Gasteiz)

All fetcher modules live in `backend/services/fetchers/` and write to a shared dict in `_store.py` (`latest_data`) protected by a threading lock. The scheduler runs fetchers in parallel via `ThreadPoolExecutor`.

**Enrichment databases** (loaded once at import from `backend/data/`):
- `plane_alert_db.json` + `tracked_names.json` — notable aircraft (POTUS, oligarchs, agencies)
- `yacht_alert_db.json` — billionaire superyachts
- `plan_ccg_vessels.json` — Chinese navy/coast guard vessels

**Network resilience:** `services/network_utils.py::fetch_with_curl()` tries Python requests first, falls back to system curl, with per-domain circuit breakers.

### API Endpoints (28 total)

**Live data:**
- `GET /api/live-data/fast` — Fast-changing data (flights, ships, satellites, UAVs, GPS jamming) with ETag + bbox filtering (`s,w,n,e` params)
- `GET /api/live-data/slow` — Slow-changing data (news, stocks, earthquakes, weather, fires, frontlines, GDELT) with ETag + bbox filtering
- `GET /api/live-data` — Full unfiltered data dict (all sources)
- `GET /api/refresh` — Force background refresh of all sources (rate-limited 2/min)
- `GET /api/debug-latest` — List keys in the data store (debug)

**Vessels & flights:**
- `POST /api/viewport` — Frontend sends map bounds to filter AIS stream and flight viewport
- `POST /api/ais/feed` — Ingest AIS-catcher HTTP JSON feed
- `GET /api/route/{callsign}` — Flight route lookup (origin/destination via adsb.lol)

**Geospatial & intelligence:**
- `GET /api/geocode` — Gazetteer search for strategic locations (`q` param)
- `GET /api/region-dossier` — Intelligence dossier for a lat/lng coordinate
- `GET /api/sentinel2/search` — Sentinel-2 satellite imagery search at lat/lng

**Radio scanner:**
- `GET /api/radio/top` — Top Broadcastify scanner feeds
- `GET /api/radio/openmhz/systems` — List OpenMHz trunked radio systems
- `GET /api/radio/openmhz/calls/{sys_name}` — Recent calls for an OpenMHz system
- `GET /api/radio/nearest` — Nearest OpenMHz system to lat/lng
- `GET /api/radio/nearest-list` — Multiple nearest systems (configurable `limit`, max 20)

**AI assistant:**
- `POST /api/assistant/query` — Question with dashboard context, returns JSON
- `POST /api/assistant/query/stream` — Streaming version (SSE)
- `POST /api/assistant/brief` — LLM-generated viewport briefing for a bounding box
- `POST /api/assistant/transcribe` — Speech-to-text via OpenAI `gpt-4o-mini-transcribe` (multipart audio upload, max 25 MB)
- `POST /api/assistant/tts` — Text-to-speech via OpenAI `tts-1` (streams `audio/mpeg`)

**Settings** (protected by `X-Admin-Key` except news-feeds GET):
- `GET /api/settings/api-keys` — List configured API keys (masked)
- `PUT /api/settings/api-keys` — Update an API key in `.env`
- `GET /api/settings/news-feeds` — Current news feed config (no auth)
- `PUT /api/settings/news-feeds` — Save new feeds (max 20)
- `POST /api/settings/news-feeds/reset` — Reset feeds to defaults

**System:**
- `GET /api/health` — Status, source counts, freshness timestamps, uptime
- `POST /api/system/update` — Download latest release, backup, extract, restart (admin)

### Frontend Data Flow

Single-page app in `frontend/src/app/page.tsx` (`Dashboard` component).

**API Proxy:** `src/app/api/[...path]/route.ts` is a catch-all that proxies all `/api/*` requests to the backend using `BACKEND_URL` (read at request time, not baked into the build). Client code always uses relative paths like `/api/live-data/fast`.

**Polling:** `src/hooks/useDataPolling.ts` polls two tiers:
- Fast: every 15s (flights, ships, satellites, GPS jamming) — 3s during startup burst
- Slow: every 120s (news, stocks, earthquakes, weather) — 5s during startup burst
- Uses ETag conditional requests (`If-None-Match`) for bandwidth savings

**Map:** `MaplibreViewer.tsx` is the core rendering component, loaded via `next/dynamic` with SSR disabled. GeoJSON builders in `src/components/map/geoJSONBuilders.ts` convert API data to map layers.

**State:** React context (`DashboardDataContext`) + hooks. No external state library.

**Voice:** Military radio-style voice interface — wake word ("Jarvis") + VAD recording + cloud STT/TTS. See `docs/voice.md` for architecture, hooks, design decisions, and costs.

## Key Patterns

- **`@/*` path alias** maps to `src/*` in both TypeScript and Vitest configs
- **ETag caching** on both fast and slow endpoints — frontend sends `If-None-Match`, backend returns `304 Not Modified` when data hasn't changed
- **Bbox filtering** — API accepts `s,w,n,e` query params for server-side geographic filtering with 20% padding
- **`@with_retry` decorator** (`services/fetchers/retry.py`) — exponential backoff with jitter for all fetcher functions
- **Docker secrets support** — backend reads `*_FILE` env vars (e.g., `AIS_API_KEY_FILE`) at startup
- **Standalone Next.js output** — `output: "standalone"` in `next.config.ts` for minimal Docker images
- **Playwright** is used in the backend for scraping (Chromium, installed separately via `python -m playwright install chromium`)

## Environment Variables

Backend (`backend/.env`):
- `AIS_API_KEY` — aisstream.io WebSocket key (recommended, ships layer)
- `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` — OpenSky OAuth2 (optional, higher rate limits)
- `LTA_ACCOUNT_KEY` — Singapore traffic cameras (optional)
- `ADMIN_KEY` — Protects settings/update endpoints (required for production)
- `CORS_ORIGINS` — Comma-separated allowed origins (auto-detects LAN if unset)

Voice (backend):
- `TTS_OPENAI_API_KEY` — OpenAI key for STT + TTS (falls back to `OPENAI_API_KEY`)

Frontend (runtime):
- `BACKEND_URL` — Backend URL for API proxy (default: `http://localhost:8000`, Docker: `http://backend:8000`)
- `NEXT_PUBLIC_PICOVOICE_ACCESS_KEY` — Picovoice key for wake word (see `docs/voice.md`)

## Deployment (Railway)

The backend runs on Railway as a single Docker service. The frontend is bundled into the backend's Next.js standalone output or deployed separately.

### Railway CLI Deploy
```bash
# CRITICAL: railway up walks up to the git root for its upload context, NOT CWD.
# You MUST use --path-as-root to force it to use the CWD as the build root.
# Without --path-as-root, Railway uploads the entire repo and may auto-detect
# the wrong builder (e.g., Railpack picks up start.sh instead of Dockerfile).

railway service backend   # switch to the correct service first
cd backend && railway up --path-as-root . --detach

railway service frontend  # switch before deploying frontend
cd frontend && railway up --path-as-root . --detach
```

### Railway Config
- **`RAILWAY_ROOT_DIRECTORY=frontend`** is set on the frontend service so GitHub-triggered deploys find `frontend/Dockerfile`
- **`RAILWAY_ROOT_DIRECTORY=backend`** is set on the backend service so GitHub-triggered deploys find `backend/Dockerfile`
- **`RAILWAY_DOCKERFILE_PATH=Dockerfile`** — relative to root directory (backend only)
- For `railway up`, use `--path-as-root .` to ensure CWD is the build context (otherwise Railway uses the git root, causing Railpack to detect `start.sh` instead of the Dockerfile)
- Railway auto-redeploys when variables are changed — this can override an in-progress `railway up` deploy

### Railway Variables
Set via `railway variables set KEY=VALUE` or the dashboard. Key Railway-specific vars:

**Backend service:**
- `PORT=8000` — Railway routes traffic to this port
- `RAILWAY_ROOT_DIRECTORY=backend` — tells Railway where to find the Dockerfile for GitHub deploys
- `RAILWAY_DOCKERFILE_PATH=Dockerfile` — relative to root directory
- `NIXPACKS_NO_INSTALL=1` — forces Dockerfile-based builds (disables Nixpacks auto-detection)

**Frontend service:**
- `PORT=3000` — Railway routes traffic to this port
- `RAILWAY_ROOT_DIRECTORY=frontend` — tells Railway where to find the Dockerfile for GitHub deploys
- `BACKEND_URL=http://backend.railway.internal:8000` — internal Railway networking

All other env vars (API keys, LLM config) are set as Railway service variables and injected at runtime.

### Playwright E2E Tests
Run before deploying to verify UI behavior:
```bash
cd frontend && python3 e2e_review_fixes.py   # 15 tests for recent fixes
cd frontend && python3 e2e_test.py            # 34 comprehensive tests
```
Requires: dev servers running on :3000 (frontend) and :8000 (backend).

### Build Notes
- The backend Docker image is large (~1.5GB) because it includes Playwright + Chromium for web scraping
- Full rebuilds take 3-5 minutes; cached rebuilds ~20 seconds
- The `playwright install --with-deps chromium` step installs Chromium + system dependencies

## CI

GitHub Actions (`.github/workflows/ci.yml`): runs `vitest` for frontend and `pytest` for backend on push/PR to main. Python 3.11, Node 20.

Docker images published to GHCR (`.github/workflows/docker-publish.yml`): multi-arch builds (amd64 + arm64) on push to main or version tags.

## Code Review Workflow

Before deploying, run these review agents in order:

1. **`superpowers:code-reviewer`** — After completing a planned milestone. Checks implementation against the plan and coding standards. Has write access.

2. **`feature-dev:code-reviewer`** — Before merge/deploy. Finds bugs, logic errors, security vulnerabilities, and convention violations. Uses confidence-based filtering to report only high-priority issues. Read-only.

3. **`code-simplifier:code-simplifier`** — After code is functionally correct. Simplifies and refines for clarity, consistency, and maintainability. Focuses on recently modified code. Has write access.

The `/simplify` skill can also be used for targeted simplification of specific files.

Run tests after each stage.

## Related Docs

- `docs/voice.md` — Voice communication architecture, hooks, design decisions, costs
- `frontend/README.md` — API URL configuration and theming
- `helm/chart/README.md` — Kubernetes Helm chart deployment
- `test-silo/` — Phase 0 product research (archetypes, market analysis, roadmap). Snapshot from March 2026, not actively maintained.
