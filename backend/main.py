import os
import time
import logging

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
_start_time = time.time()

# ---------------------------------------------------------------------------
# Docker Swarm Secrets support
# For each VAR below, if VAR_FILE is set (e.g. AIS_API_KEY_FILE=/run/secrets/AIS_API_KEY),
# the file is read and its trimmed content is placed into VAR.
# This MUST run before service imports — modules read os.environ at import time.
# ---------------------------------------------------------------------------
_SECRET_VARS = [
    "AIS_API_KEY",
    "OPENSKY_CLIENT_ID",
    "OPENSKY_CLIENT_SECRET",
    "LTA_ACCOUNT_KEY",
    "CORS_ORIGINS",
    "ADMIN_KEY",
    "TTS_OPENAI_API_KEY",
]

for _var in _SECRET_VARS:
    _file_var = f"{_var}_FILE"
    _file_path = os.environ.get(_file_var)
    if _file_path:
        try:
            with open(_file_path, "r") as _f:
                _value = _f.read().strip()
            if _value:
                os.environ[_var] = _value
                logger.info(f"Loaded secret {_var} from {_file_path}")
            else:
                logger.warning(f"Secret file {_file_path} for {_var} is empty")
        except FileNotFoundError:
            logger.error(f"Secret file {_file_path} for {_var} not found")
        except Exception as _e:
            logger.error(f"Failed to read secret file {_file_path} for {_var}: {_e}")

import hashlib
import json as json_mod
import socket
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response, Query, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import StreamingResponse, JSONResponse

from services.api_settings import get_api_keys, update_api_key
from services.ais_stream import start_ais_stream, stop_ais_stream
from services.carrier_tracker import start_carrier_tracker, stop_carrier_tracker
from services.data_fetcher import (
    start_scheduler, stop_scheduler, get_latest_data,
    source_timestamps, update_all_data,
)
from services.llm_assistant import (
    call_llm, call_llm_streaming, search_entities,
    build_briefing_context, build_briefing_prompt,
    ContentFilterError, LLMConnectionError,
)
from services.voice import transcribe, tts_stream, AVAILABLE_VOICES, ALLOWED_AUDIO_TYPES, _get_api_key
from services.network_utils import fetch_with_curl
from services.news_feed_config import get_feeds, save_feeds, reset_feeds
from services.radio_intercept import (
    get_top_broadcastify_feeds, get_openmhz_systems,
    get_recent_openmhz_calls, find_nearest_openmhz_system,
    find_nearest_openmhz_systems_list,
)
from services.region_dossier import get_region_dossier
from services.schemas import HealthResponse, RefreshResponse
from services.sentinel_search import search_sentinel2_scene
from services.thermal_sentinel import analyze_thermal
from services.shodan_connector import search_shodan
from services.updater import perform_update, schedule_restart

limiter = Limiter(key_func=get_remote_address)

_ARTIFACT_CSP = (
    "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
    "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
    "img-src * data: blob:; connect-src *"
)

# ---------------------------------------------------------------------------
# Admin authentication — protects settings & system endpoints
# Set ADMIN_KEY in .env or Docker secrets. If unset, endpoints remain open
# for local-dev convenience but will log a startup warning.
# ---------------------------------------------------------------------------
_ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
if not _ADMIN_KEY:
    logger.warning("ADMIN_KEY is not set — sensitive endpoints are UNPROTECTED. "
                   "Set ADMIN_KEY in .env or Docker secrets for production.")

def require_admin(request: Request):
    """FastAPI dependency that rejects requests without a valid X-Admin-Key header."""
    if not _ADMIN_KEY:
        return  # No key configured — allow all (local dev)
    if request.headers.get("X-Admin-Key") != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden — invalid or missing admin key")


def _build_cors_origins():
    """Build a CORS origins whitelist: localhost + LAN IPs + env overrides.
    Falls back to wildcard only if auto-detection fails entirely."""
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    # Add this machine's LAN IPs (covers common home/office setups)
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ("127.0.0.1", "0.0.0.0"):
                origins.append(f"http://{ip}:3000")
                origins.append(f"http://{ip}:8000")
    except Exception:
        pass
    # Allow user override via CORS_ORIGINS env var (comma-separated)
    extra = os.environ.get("CORS_ORIGINS", "")
    if extra:
        origins.extend([o.strip() for o in extra.split(",") if o.strip()])
    return list(set(origins))  # deduplicate

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate environment variables before starting anything
    from services.env_check import validate_env
    validate_env(strict=True)

    # Start AIS stream first — it loads the disk cache (instant ships) then
    # begins accumulating live vessel data via WebSocket in the background.
    start_ais_stream()

    # Carrier tracker runs its own initial update_carrier_positions() internally
    # in _scheduler_loop, so we do NOT call it again in the preload thread.
    start_carrier_tracker()

    # Start the recurring scheduler (fast=60s, slow=30min).
    start_scheduler()

    # Kick off the full data preload in a background thread so the server
    # is listening on port 8000 instantly.  The frontend's adaptive polling
    # (retries every 3s) will pick up data piecemeal as each fetcher finishes.
    def _background_preload():
        logger.info("=== PRELOADING DATA (background — server already accepting requests) ===")
        try:
            update_all_data()
            logger.info("=== PRELOAD COMPLETE ===")
        except Exception as e:
            logger.error(f"Data preload failed (non-fatal): {e}")

    threading.Thread(target=_background_preload, daemon=True).start()

    yield
    # Shutdown: Stop all background services
    stop_ais_stream()
    stop_scheduler()
    stop_carrier_tracker()

app = FastAPI(title="Live Risk Dashboard API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_refresh_lock = threading.Lock()

@app.get("/api/refresh", response_model=RefreshResponse)
@limiter.limit("2/minute")
async def force_refresh(request: Request):
    if not _refresh_lock.acquire(blocking=False):
        return {"status": "refresh already in progress"}
    def _do_refresh():
        try:
            update_all_data()
        finally:
            _refresh_lock.release()
    t = threading.Thread(target=_do_refresh)
    t.start()
    return {"status": "refreshing in background"}

@app.post("/api/ais/feed")
@limiter.limit("60/minute")
async def ais_feed(request: Request):
    """Accept AIS-catcher HTTP JSON feed (POST decoded AIS messages)."""
    from services.ais_stream import ingest_ais_catcher
    try:
        body = await request.json()
    except Exception:
        return Response(content='{"error":"invalid JSON"}', status_code=400, media_type="application/json")

    msgs = body.get("msgs", [])
    if not msgs:
        return {"status": "ok", "ingested": 0}

    count = ingest_ais_catcher(msgs)
    return {"status": "ok", "ingested": count}

class ViewportUpdate(BaseModel):
    s: float
    w: float
    n: float
    e: float

@app.post("/api/viewport")
@limiter.limit("60/minute")
async def update_viewport(vp: ViewportUpdate, request: Request):
    """Receive frontend map bounds — updates AIS stream + flight viewport."""
    from services.ais_stream import update_ais_bbox
    import services.fetchers._store as _store
    # Add a gentle 10% padding so ships don't pop-in right at the edge
    pad_lat = (vp.n - vp.s) * 0.1
    # handle antimeridian bounding box padding later if needed, simple for now:
    pad_lng = (vp.e - vp.w) * 0.1 if vp.e > vp.w else 0

    update_ais_bbox(
        south=max(-90, vp.s - pad_lat),
        west=max(-180, vp.w - pad_lng) if pad_lng else vp.w,
        north=min(90, vp.n + pad_lat),
        east=min(180, vp.e + pad_lng) if pad_lng else vp.e
    )
    # Also store viewport for flight fetcher dead-zone detection
    _store._current_viewport = {"s": vp.s, "w": vp.w, "n": vp.n, "e": vp.e}
    return {"status": "ok"}

@app.get("/api/geocode")
async def geocode(q: str = ""):
    """Lightweight gazetteer lookup — returns matching locations for the search bar."""
    from services.geo_gazetteer import STRATEGIC_LOCATIONS
    if not q or len(q) < 2:
        return {"results": []}
    query = q.lower().strip()
    matches = []
    for name, loc in STRATEGIC_LOCATIONS.items():
        if query in name or name in query:
            matches.append({
                "name": name.title(),
                "lat": loc["lat"],
                "lng": loc["lng"],
                "radius_km": loc["radius_km"],
            })
    matches.sort(key=lambda m: (m["name"].lower() != query, len(m["name"])))
    return {"results": matches[:8]}

@app.get("/api/live-data")
@limiter.limit("120/minute")
async def live_data(request: Request):
    return get_latest_data()

def _etag_response(request: Request, payload: dict, prefix: str = "", default=None):
    """Serialize once, hash the bytes for ETag, return 304 or full response."""
    content = json_mod.dumps(payload, default=default)
    etag = hashlib.md5(f"{prefix}{content}".encode()).hexdigest()[:16]
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "no-cache"})
    return Response(content=content, media_type="application/json",
                    headers={"ETag": etag, "Cache-Control": "no-cache"})

def _bbox_filter(items: list, s: float, w: float, n: float, e: float,
                 lat_key: str = "lat", lng_key: str = "lng") -> list:
    """Filter a list of dicts to those within the bounding box (with 20% padding).
    Handles antimeridian crossing (e.g. w=170, e=-170)."""
    pad_lat = (n - s) * 0.2
    pad_lng = (e - w) * 0.2 if e > w else ((e + 360 - w) * 0.2)
    s2, n2 = s - pad_lat, n + pad_lat
    w2, e2 = w - pad_lng, e + pad_lng
    crosses_antimeridian = w2 > e2
    out = []
    for item in items:
        lat = item.get(lat_key)
        lng = item.get(lng_key)
        if lat is None or lng is None:
            out.append(item)  # Keep items without coords (don't filter them out)
            continue
        if not (s2 <= lat <= n2):
            continue
        if crosses_antimeridian:
            if lng >= w2 or lng <= e2:
                out.append(item)
        else:
            if w2 <= lng <= e2:
                out.append(item)
    return out

@app.get("/api/live-data/fast")
@limiter.limit("120/minute")
async def live_data_fast(request: Request,
                         s: float = Query(None, description="South bound"),
                         w: float = Query(None, description="West bound"),
                         n: float = Query(None, description="North bound"),
                         e: float = Query(None, description="East bound")):
    d = get_latest_data()
    has_bbox = all(v is not None for v in (s, w, n, e))
    def _f(items, lat_key="lat", lng_key="lng"):
        return _bbox_filter(items, s, w, n, e, lat_key, lng_key) if has_bbox else items
    payload = {
        "commercial_flights": _f(d.get("commercial_flights", [])),
        "military_flights": _f(d.get("military_flights", [])),
        "private_flights": _f(d.get("private_flights", [])),
        "private_jets": _f(d.get("private_jets", [])),
        "tracked_flights": d.get("tracked_flights", []),  # Always send tracked (small set)
        "ships": _f(d.get("ships", [])),
        "cctv": _f(d.get("cctv", []), lat_key="lat", lng_key="lon"),
        "uavs": _f(d.get("uavs", [])),
        "liveuamap": _f(d.get("liveuamap", [])),
        "gps_jamming": _f(d.get("gps_jamming", [])),
        "ukraine_alerts": _f(d.get("ukraine_alerts", [])),
        "trains": _f(d.get("trains", [])),
        "satellites": _f(d.get("satellites", [])),
        "satellite_source": d.get("satellite_source", "none"),
        "freshness": dict(source_timestamps),
    }
    bbox_tag = f"{s},{w},{n},{e}" if has_bbox else "full"
    return _etag_response(request, payload, prefix=f"fast|{bbox_tag}|")

@app.get("/api/live-data/slow")
@limiter.limit("60/minute")
async def live_data_slow(request: Request,
                         s: float = Query(None, description="South bound"),
                         w: float = Query(None, description="West bound"),
                         n: float = Query(None, description="North bound"),
                         e: float = Query(None, description="East bound")):
    d = get_latest_data()
    has_bbox = all(v is not None for v in (s, w, n, e))
    def _f(items, lat_key="lat", lng_key="lng"):
        return _bbox_filter(items, s, w, n, e, lat_key, lng_key) if has_bbox else items
    payload = {
        "last_updated": d.get("last_updated"),
        "news": d.get("news", []),  # News has coords but we always send it (small set, important)
        "stocks": d.get("stocks", {}),
        "oil": d.get("oil", {}),
        "weather": d.get("weather"),
        "traffic": d.get("traffic", []),
        "earthquakes": _f(d.get("earthquakes", [])),
        "frontlines": d.get("frontlines"),  # Always send (GeoJSON polygon, not point-filterable)
        "gdelt": d.get("gdelt", []),  # GeoJSON features — filtered client-side
        "airports": d.get("airports", []),  # Always send (reference data)
        "kiwisdr": _f(d.get("kiwisdr", []), lat_key="lat", lng_key="lon"),
        "space_weather": d.get("space_weather"),
        "internet_outages": _f(d.get("internet_outages", [])),
        "firms_fires": _f(d.get("firms_fires", [])),
        "datacenters": _f(d.get("datacenters", [])),
        "military_bases": _f(d.get("military_bases", [])),
        "power_plants": _f(d.get("power_plants", [])),
        "coverage_gaps": d.get("coverage_gaps", []),
        "correlations": d.get("correlations", []),
        "disease_outbreaks": d.get("disease_outbreaks", []),
        "prediction_markets": d.get("prediction_markets", []),
        "trending_markets": d.get("trending_markets", []),
        "fimi": _f(d.get("fimi", [])),
        "meshtastic": _f(d.get("meshtastic", [])),
        "correlation_alerts": d.get("correlation_alerts", []),
        "freshness": dict(source_timestamps),
    }
    bbox_tag = f"{s},{w},{n},{e}" if has_bbox else "full"
    return _etag_response(request, payload, prefix=f"slow|{bbox_tag}|", default=str)

@app.get("/api/debug-latest")
@limiter.limit("30/minute")
async def debug_latest_data(request: Request):
    return list(get_latest_data().keys())


@app.get("/api/health", response_model=HealthResponse)
@limiter.limit("30/minute")
async def health_check(request: Request):
    d = get_latest_data()
    last = d.get("last_updated")
    return {
        "status": "ok",
        "last_updated": last,
        "sources": {
            "flights": len(d.get("commercial_flights", [])),
            "military": len(d.get("military_flights", [])),
            "ships": len(d.get("ships", [])),
            "satellites": len(d.get("satellites", [])),
            "earthquakes": len(d.get("earthquakes", [])),
            "cctv": len(d.get("cctv", [])),
            "news": len(d.get("news", [])),
            "uavs": len(d.get("uavs", [])),
            "firms_fires": len(d.get("firms_fires", [])),
            "liveuamap": len(d.get("liveuamap", [])),
            "gdelt": len(d.get("gdelt", [])),
        },
        "freshness": dict(source_timestamps),
        "uptime_seconds": round(time.time() - _start_time),
    }



@app.get("/api/radio/top")
@limiter.limit("30/minute")
async def get_top_radios(request: Request):
    return get_top_broadcastify_feeds()

@app.get("/api/radio/openmhz/systems")
@limiter.limit("30/minute")
async def api_get_openmhz_systems(request: Request):
    return get_openmhz_systems()

@app.get("/api/radio/openmhz/calls/{sys_name}")
@limiter.limit("60/minute")
async def api_get_openmhz_calls(request: Request, sys_name: str):
    return get_recent_openmhz_calls(sys_name)

@app.get("/api/radio/nearest")
@limiter.limit("60/minute")
async def api_get_nearest_radio(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    return find_nearest_openmhz_system(lat, lng)

@app.get("/api/radio/nearest-list")
@limiter.limit("60/minute")
async def api_get_nearest_radios_list(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    limit: int = Query(5, ge=1, le=20),
):
    return find_nearest_openmhz_systems_list(lat, lng, limit=limit)

@app.get("/api/route/{callsign}")
@limiter.limit("60/minute")
async def get_flight_route(request: Request, callsign: str, lat: float = 0.0, lng: float = 0.0):
    r = fetch_with_curl("https://api.adsb.lol/api/0/routeset", method="POST", json_data={"planes": [{"callsign": callsign, "lat": lat, "lng": lng}]}, timeout=10)
    if r and r.status_code == 200:
        data = r.json()
        route_list = []
        if isinstance(data, dict):
            route_list = data.get("value", [])
        elif isinstance(data, list):
            route_list = data
        
        if route_list:
            route = route_list[0]
            airports = route.get("_airports", [])
            if len(airports) >= 2:
                orig = airports[0]
                dest = airports[-1]
                return {
                    "orig_loc": [orig.get("lon", 0), orig.get("lat", 0)],
                    "dest_loc": [dest.get("lon", 0), dest.get("lat", 0)],
                    "origin_name": f"{orig.get('iata', '') or orig.get('icao', '')}: {orig.get('name', 'Unknown')}",
                    "dest_name": f"{dest.get('iata', '') or dest.get('icao', '')}: {dest.get('name', 'Unknown')}",
                }
    return {}

@app.get("/api/region-dossier")
@limiter.limit("30/minute")
def api_region_dossier(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    """Sync def so FastAPI runs it in a threadpool — prevents blocking the event loop."""
    return get_region_dossier(lat, lng)

@app.get("/api/sentinel2/search")
@limiter.limit("30/minute")
def api_sentinel2_search(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    """Search for latest Sentinel-2 imagery at a point. Sync for threadpool execution."""
    return search_sentinel2_scene(lat, lng)

# ---------------------------------------------------------------------------
# Thermal Sentinel — on-demand SWIR anomaly analysis
# ---------------------------------------------------------------------------

class ThermalRequest(BaseModel):
    lat: float
    lng: float

@app.post("/api/thermal/analyze")
@limiter.limit("20/minute")
def api_thermal_analyze(request: Request, body: ThermalRequest):
    """Thermal anomaly analysis at a point. Sync for threadpool execution."""
    return analyze_thermal(body.lat, body.lng)

# ---------------------------------------------------------------------------
# Shodan — on-demand exposed-device search (admin-only)
# ---------------------------------------------------------------------------

class ShodanSearchRequest(BaseModel):
    query: str
    limit: int = 20

@app.post("/api/shodan/search", dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
def api_shodan_search(request: Request, body: ShodanSearchRequest):
    """Search Shodan for exposed devices. Admin-only. Sync for threadpool."""
    return search_shodan(body.query, body.limit)

# ---------------------------------------------------------------------------
# API Settings — key registry & management
# ---------------------------------------------------------------------------

class ApiKeyUpdate(BaseModel):
    env_key: str
    value: str

@app.get("/api/settings/api-keys", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def api_get_keys(request: Request):
    return get_api_keys()

@app.put("/api/settings/api-keys", dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
async def api_update_key(request: Request, body: ApiKeyUpdate):
    ok = update_api_key(body.env_key, body.value)
    if ok:
        # Refresh LLM providers if an LLM key was updated
        if body.env_key in ("CEREBRAS_API_KEY", "LLM_API_KEY", "CEREBRAS_BASE_URL",
                            "LLM_BASE_URL", "CEREBRAS_MODEL", "LLM_MODEL"):
            try:
                from services.llm_assistant import refresh_providers
                refresh_providers()
            except Exception as e:
                logger.warning(f"Failed to refresh LLM providers: {e}")
        return {"status": "updated", "env_key": body.env_key}
    return {"status": "error", "message": "Failed to update .env file"}

# ---------------------------------------------------------------------------
# News Feed Configuration
# ---------------------------------------------------------------------------

@app.get("/api/settings/news-feeds")
@limiter.limit("30/minute")
async def api_get_news_feeds(request: Request):
    return get_feeds()

@app.put("/api/settings/news-feeds", dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
async def api_save_news_feeds(request: Request):
    body = await request.json()
    ok = save_feeds(body)
    if ok:
        return {"status": "updated", "count": len(body)}
    return Response(
        content=json_mod.dumps({"status": "error", "message": "Validation failed (max 20 feeds, each needs name/url/weight 1-5)"}),
        status_code=400,
        media_type="application/json",
    )

@app.post("/api/settings/news-feeds/reset", dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
async def api_reset_news_feeds(request: Request):
    ok = reset_feeds()
    if ok:
        return {"status": "reset", "feeds": get_feeds()}
    return {"status": "error", "message": "Failed to reset feeds"}

# ---------------------------------------------------------------------------
# System — self-update
# ---------------------------------------------------------------------------

@app.post("/api/system/update", dependencies=[Depends(require_admin)])
@limiter.limit("1/minute")
async def system_update(request: Request):
    """Download latest release, backup current files, extract update, and restart."""
    # In Docker, __file__ is /app/main.py so .parent.parent resolves to /
    # which causes PermissionError. Use cwd as fallback when parent.parent
    # doesn't contain frontend/ or backend/ (i.e. we're already at project root).
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "frontend").is_dir() or (candidate / "backend").is_dir():
        project_root = str(candidate)
    else:
        project_root = os.getcwd()
    result = perform_update(project_root)
    if result.get("status") == "error":
        return Response(
            content=json_mod.dumps(result),
            status_code=500,
            media_type="application/json",
        )
    # Schedule restart AFTER response flushes (2s delay)
    threading.Timer(2.0, schedule_restart, args=[project_root]).start()
    return result

# ---------------------------------------------------------------------------
# Snapshots — capture & list frozen feed data for demo mode
# ---------------------------------------------------------------------------

_SNAPSHOT_DIR = Path(os.environ.get(
    "SNAPSHOT_DIR",
    str(Path(__file__).resolve().parent.parent / "frontend" / "public" / "snapshots"),
))


@app.post("/api/snapshots/capture", dependencies=[Depends(require_admin)])
@limiter.limit("5/minute")
async def snapshot_capture(request: Request, key: str = Query(..., min_length=1, max_length=100,
                                                              pattern=r"^[a-zA-Z0-9_-]+$")):
    """Capture a frozen snapshot of all current feed data for demo mode."""
    data = get_latest_data()
    data["freshness"] = dict(source_timestamps)
    data["_snapshot_meta"] = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "key": key,
    }
    _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _SNAPSHOT_DIR / f"{key}.json"
    out_path.write_text(json_mod.dumps(data, default=str), encoding="utf-8")
    size_mb = round(out_path.stat().st_size / (1024 * 1024), 2)
    logger.info(f"Snapshot captured: {key} ({size_mb} MB)")
    return {"status": "ok", "key": key, "size_mb": size_mb}


@app.get("/api/snapshots/list", dependencies=[Depends(require_admin)])
@limiter.limit("30/minute")
async def snapshot_list(request: Request):
    """List available snapshots and overlays."""
    if not _SNAPSHOT_DIR.is_dir():
        return {"snapshots": []}
    files = sorted(f.name for f in _SNAPSHOT_DIR.glob("*.json") if f.name != ".gitkeep")
    return {"snapshots": files}


# ---------------------------------------------------------------------------
# AI Assistant
# ---------------------------------------------------------------------------

class AssistantQuery(BaseModel):
    query: str
    viewport: dict | None = None
    conversation: list | None = None
    active_artifact: dict | None = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()

_SUMMARY_KEYS = [
    "commercial_flights", "private_flights", "private_jets",
    "military_flights", "tracked_flights", "ships", "satellites",
    "earthquakes", "firms_fires", "internet_outages", "gdelt",
    "kiwisdr", "datacenters", "military_bases", "power_plants", "cctv",
    "disease_outbreaks",
]

def _build_data_summary(data: dict) -> dict:
    """Build data summary with counts and rich context for LLM situational awareness."""
    summary: dict = {
        key: len(items)
        for key in _SUMMARY_KEYS
        if (items := data.get(key)) and isinstance(items, list)
    }
    if (gaps := data.get("coverage_gaps")) and isinstance(gaps, list):
        summary["coverage_gaps_count"] = len(gaps)
    if (corrs := data.get("correlations")) and isinstance(corrs, list):
        summary["correlations_count"] = len(corrs)

    # Rich context for LLM situational awareness
    news = data.get("news", [])
    if news:
        summary["top_headlines"] = [
            {"title": n.get("title", ""), "source": n.get("source", ""), "risk_score": n.get("risk_score", 0)}
            for n in sorted(news, key=lambda x: x.get("risk_score", 0), reverse=True)[:10]
        ]

    stocks = data.get("stocks", {})
    oil = data.get("oil", {})
    if stocks or oil:
        summary["markets"] = {
            "stocks": {k: {"price": v.get("price"), "change": v.get("change_percent")} for k, v in stocks.items()},
            "oil": {k: {"price": v.get("price"), "change": v.get("change_percent")} for k, v in oil.items()},
        }

    if gaps:
        summary["top_coverage_gaps"] = [
            {"lat": g.get("lat"), "lon": g.get("lon"), "gdelt_count": g.get("gdelt_count", 0),
             "top_event_codes": g.get("top_event_codes", [])}
            for g in sorted(gaps, key=lambda x: x.get("gdelt_count", 0), reverse=True)[:5]
        ]

    if corrs:
        summary["top_correlations"] = [
            {"type": c.get("type"), "distance_km": c.get("distance_km"),
             "entity": (c.get("entity") or {}).get("flight") or c.get("entity_name") or c.get("conflict_location", "?"),
             "gdelt_count": c.get("gdelt_count", 0)}
            for c in corrs[:3]
        ]

    outbreaks = data.get("disease_outbreaks", [])
    if outbreaks:
        summary["recent_outbreaks"] = [
            {"disease": o.get("disease_name", ""), "country": o.get("country", ""), "date": o.get("pub_date", "")}
            for o in outbreaks[:5]
        ]

    return summary

@app.post("/api/assistant/query")
@limiter.limit("10/minute")
async def assistant_query(request: Request, body: AssistantQuery):
    """Ask the AI assistant a question about the current dashboard state."""
    data = get_latest_data()
    data_summary = _build_data_summary(data)
    search_results = search_entities(body.query, data, viewport=body.viewport)

    try:
        result = call_llm(
            query=body.query,
            data_summary=data_summary,
            viewport=body.viewport,
            conversation=body.conversation,
            search_results=search_results,
            live_data=data,
        )
        return result
    except ContentFilterError as e:
        return Response(
            content=json_mod.dumps({"error": str(e), "error_type": "content_filter"}),
            status_code=422,
            media_type="application/json",
        )
    except (LLMConnectionError, RuntimeError) as e:
        return Response(
            content=json_mod.dumps({"error": str(e), "error_type": "connection"}),
            status_code=503,
            media_type="application/json",
        )

@app.post("/api/assistant/query/stream")
@limiter.limit("10/minute")
async def assistant_query_stream(request: Request, body: AssistantQuery):
    """Streaming version — yields SSE events for real-time progress."""
    data = get_latest_data()
    data_summary = _build_data_summary(data)
    search_results = search_entities(body.query, data, viewport=body.viewport)

    def generate():
        yield from call_llm_streaming(
            query=body.query,
            data_summary=data_summary,
            viewport=body.viewport,
            conversation=body.conversation,
            search_results=search_results,
            live_data=data,
            active_artifact=body.active_artifact,
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ---------------------------------------------------------------------------
# Voice: Transcription (STT) and Text-to-Speech (TTS)
# ---------------------------------------------------------------------------

class TTSRequest(BaseModel):
    text: str
    voice: str = "onyx"


@app.post("/api/assistant/transcribe")
@limiter.limit("15/minute")
async def assistant_transcribe(request: Request, file: UploadFile = File(...)):
    """Transcribe uploaded audio to text via OpenAI STT."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25 MB limit (OpenAI max)
        raise HTTPException(status_code=400, detail="Audio file too large (max 25 MB)")

    content_type = file.content_type or "audio/webm"
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {content_type}",
        )

    try:
        result = await transcribe(audio_bytes, content_type)
        return result
    except RuntimeError as e:
        status = 503 if "not set" in str(e) else 500
        return Response(
            content=json_mod.dumps({"error": str(e)}),
            status_code=status,
            media_type="application/json",
        )


@app.post("/api/assistant/tts")
@limiter.limit("15/minute")
async def assistant_tts(request: Request, body: TTSRequest):
    """Generate speech audio from text via OpenAI TTS. Returns streaming MP3."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    if len(body.text) > 4096:
        raise HTTPException(status_code=400, detail="Text too long (max 4096 chars)")

    # Validate API key eagerly — tts_stream is an async generator so errors
    # during iteration would produce a truncated 200 response, not a clean error.
    try:
        _get_api_key()
    except RuntimeError as e:
        return Response(
            content=json_mod.dumps({"error": str(e)}),
            status_code=503,
            media_type="application/json",
        )

    return StreamingResponse(
        tts_stream(body.text, body.voice),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/assistant/voices")
async def assistant_voices():
    """List available TTS voices."""
    return {"voices": AVAILABLE_VOICES, "default": "onyx"}


@app.get("/api/artifacts")
async def list_artifacts():
    """List all available artifacts (metadata only)."""
    from services.agent.artifacts import get_artifact_store
    return get_artifact_store().list()


@app.get("/api/artifacts/registry")
async def get_artifact_registry():
    """Return the artifact registry for browsing or agent use."""
    from services.agent.artifact_registry import get_artifact_registry
    return get_artifact_registry().list_all()


@app.get("/api/artifacts/registry/search")
async def search_artifact_registry(tags: str = ""):
    """Search artifacts by tags, ranked by match count."""
    from services.agent.artifact_registry import get_artifact_registry
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    if not tag_list:
        return []
    return get_artifact_registry().search(tag_list)


@app.get("/api/artifacts/registry/{name}/versions")
async def list_artifact_versions(name: str):
    """List all versions of a registered artifact."""
    from services.agent.artifact_registry import get_artifact_registry
    result = get_artifact_registry().get_latest_version(name)
    if result is None:
        return JSONResponse({"error": "Artifact not found in registry"}, status_code=404)
    _, meta = result
    return meta.get("versions", [])


@app.get("/api/artifacts/registry/{name}")
async def get_artifact_registry_entry(name: str):
    """Get metadata and version history for a specific artifact."""
    from services.agent.artifact_registry import get_artifact_registry
    result = get_artifact_registry().get_latest_version(name)
    if result is None:
        return JSONResponse({"error": "Artifact not found in registry"}, status_code=404)
    _, meta = result
    return meta


@app.get("/api/artifacts/registry/{name}/v/{version}")
async def get_artifact_version(name: str, version: int):
    """Get a specific version of a registered artifact."""
    from services.agent.artifact_registry import get_artifact_registry
    html = get_artifact_registry().get_version(name, version)
    if html is None:
        return JSONResponse({"error": "Version not found"}, status_code=404)
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Security-Policy": _ARTIFACT_CSP},
    )


@app.get("/api/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Serve a generated artifact by ID as an HTML page."""
    from services.agent.artifacts import get_artifact_store
    store = get_artifact_store()
    art = store.get(artifact_id)
    if art is None:
        return JSONResponse({"error": "Artifact not found"}, status_code=404)
    return Response(
        content=art.html,
        media_type="text/html",
        headers={"Content-Security-Policy": _ARTIFACT_CSP},
    )


@app.get("/api/alerts")
async def list_alerts(limit: int = 50):
    """List recent proactive alerts, newest first."""
    from services.agent.alerts import get_alert_store
    return get_alert_store().list(limit=min(limit, 200))


@app.get("/api/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get a specific alert by ID."""
    from services.agent.alerts import get_alert_store
    alert = get_alert_store().get(alert_id)
    if alert is None:
        return JSONResponse({"error": "Alert not found"}, status_code=404)
    return {
        "id": alert.alert_id,
        "alert_type": alert.alert_type,
        "severity": alert.severity.value,
        "title": alert.title,
        "description": alert.description,
        "lat": alert.lat,
        "lng": alert.lng,
        "data": alert.data,
        "created_at": alert.created_at,
    }


class BriefRequest(BaseModel):
    south: float
    west: float
    north: float
    east: float

@app.post("/api/assistant/brief")
@limiter.limit("5/minute")
async def assistant_brief(request: Request, body: BriefRequest):
    """Generate a viewport briefing summarizing notable activity in the current view."""
    data = get_latest_data()
    viewport = {"south": body.south, "west": body.west, "north": body.north, "east": body.east}
    ctx = build_briefing_context(data, viewport)

    # Try LLM-enhanced summary with provider fallback
    try:
        import httpx as _httpx
        from services.llm_assistant import _PROVIDERS

        llm_summary = None
        if _PROVIDERS:
            prompt = build_briefing_prompt(ctx)
            for provider in _PROVIDERS:
                try:
                    url = f"{provider['base_url'].rstrip('/')}/chat/completions"
                    headers = {"Authorization": f"Bearer {provider['api_key']}", "Content-Type": "application/json"}
                    payload = {
                        "model": provider["model"],
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": "Brief me on what's in view."},
                        ],
                        "temperature": 0.3,
                        **({"max_completion_tokens": 512} if provider["name"] == "cerebras" else {"max_tokens": 512}),
                    }
                    resp = _httpx.post(url, json=payload, headers=headers, timeout=20.0)
                    resp.raise_for_status()
                    llm_summary = resp.json()["choices"][0]["message"].get("content", "").strip()
                    if llm_summary:
                        break
                except Exception as e:
                    logger.warning(f"Briefing [{provider['name']}] failed, trying next: {e}")
                    continue
        ctx["summary"] = llm_summary or ctx["summary_text"]
    except Exception as e:
        logger.warning(f"Briefing LLM call failed, using text summary: {e}")
        ctx["summary"] = ctx["summary_text"]

    return {
        "summary": ctx["summary"],
        "notable_entities": ctx["notable"][:20],
        "suggested_layers": ctx["suggested_layers"],
        "counts": ctx["counts"],
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
