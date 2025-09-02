import os
import json
import asyncio
import time
from typing import Optional

import redis
from celery.result import AsyncResult
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import Session, declarative_base
from starlette.middleware.cors import CORSMiddleware

from celery_app import celery_app, hello_task

# Load environment variables from api/.env
load_dotenv(override=True)

# --- Config / Clients ---
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base = declarative_base()

# Redis client (used by /healthz and /v1/*)
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# --- Example table ---
class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)

# --- FastAPI app ---
app = FastAPI()

# CORS: during dev allow your Next.js origin; we’ll tighten later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # change to your web origin in Phase 1
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Create tables automatically on startup if missing
    Base.metadata.create_all(bind=engine)

# ---------- Basic health ----------
@app.get("/health")
def health():
    return {"status": "ok"}

# ---------- Consolidated healthz (DB + Redis + Celery worker) ----------
def _check_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

def _check_redis() -> None:
    redis_client.ping()

def _check_worker() -> bool:
    # Celery broadcast ping; returns list like [{'worker@host': 'pong'}]
    pong = celery_app.control.ping(timeout=1.0)
    return bool(pong)

@app.get("/healthz")
def healthz():
    status = {"db": "down", "redis": "down", "worker": "down"}

    try:
        _check_db()
        status["db"] = "ok"
    except Exception as e:
        status["db_error"] = str(e)

    try:
        _check_redis()
        status["redis"] = "ok"
    except Exception as e:
        status["redis_error"] = str(e)

    try:
        if _check_worker():
            status["worker"] = "ok"
    except Exception as e:
        status["worker_error"] = str(e)

    return status

# ---------- ENV TEST ----------
@app.get("/env-test")
def env_test():
    return {
        "POSTGRES_USER": os.getenv("POSTGRES_USER"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
        "REDIS_URL": os.getenv("REDIS_URL"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
    }

# ---------- Database connectivity test ----------
@app.get("/ping/db")
def ping_db():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return {"db_connected": bool(result)}
    except Exception as e:
        return {"db_connected": False, "error": str(e)}

# ---------- Stocks endpoints ----------
@app.post("/stocks")
def create_stock(symbol: str, name: str | None = None):
    with Session(engine) as db:
        s = Stock(symbol=symbol.upper(), name=name)
        db.add(s)
        db.commit()
        db.refresh(s)
        return {"id": s.id, "symbol": s.symbol, "name": s.name}

@app.get("/stocks")
def list_stocks():
    with Session(engine) as db:
        rows = db.query(Stock).order_by(Stock.symbol).all()
        return [{"id": r.id, "symbol": r.symbol, "name": r.name} for r in rows]

# ---------- Celery demo endpoints ----------
@app.post("/tasks/hello")
def run_hello(name: str = "world"):
    job = hello_task.delay(name)
    return {"task_id": job.id, "status": "queued"}

@app.get("/tasks/status/{task_id}")
def task_status(task_id: str):
    res: AsyncResult = AsyncResult(task_id, app=celery_app)
    payload = {"task_id": task_id, "state": res.state}
    if res.successful():
        payload["result"] = res.result
    elif res.failed():
        payload["error"] = str(res.result)
    return payload

# ---------- API surface (read-only & cached) ----------
@app.get("/v1/tape")
def get_tape():
    """Return the mock tape array written by Celery Beat/Worker (key: fs:tape)."""
    raw = redis_client.get("fs:tape")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []

# =========================
# Step 2: Cache + Latch
# =========================

# ---- Simple cache helpers ----
DEMO_CACHE_TTL = 30  # seconds
DEMO_LATCH_TTL = 5   # seconds

def cache_set(key: str, value: str, ttl: int = DEMO_CACHE_TTL) -> bool:
    return bool(redis_client.set(key, value, ex=ttl))

def cache_get(key: str) -> Optional[str]:
    val = redis_client.get(key)
    return val

def cache_ttl(key: str) -> int:
    t = redis_client.ttl(key)
    return int(t) if t is not None else -2  # Redis: -2 = key missing, -1 = no expire

# ---- Latch (request coalescing) helpers ----
def latch_acquire(name: str, ttl: int = DEMO_LATCH_TTL) -> bool:
    """
    Try to acquire a short-lived 'latch' so only one request performs upstream work.
    Returns True if acquired (do the work), False otherwise.
    """
    return bool(redis_client.set(name, "1", nx=True, ex=ttl))

def latch_key_for(resource_key: str) -> str:
    return f"fs:latch:{resource_key}"

async def wait_for_latch_release(name: str, timeout: float = 6.0):
    """
    If we didn't acquire the latch, poll for its disappearance for up to `timeout`.
    Coalesces concurrent requests onto the first one that acquired the latch.
    """
    start = time.time()
    while time.time() - start < timeout:
        if not redis_client.exists(name):
            return
        await asyncio.sleep(0.05)

# ---- Step 2a: Simple demo cache endpoint ----
# POST /demo-cache?key=foo&value=bar -> sets value with TTL=30s
# GET  /demo-cache?key=foo          -> returns {key, value, ttl}
@app.post("/demo-cache")
def demo_cache_set(key: str = Query(...), value: str = Query(...)):
    ok = cache_set(key, value, DEMO_CACHE_TTL)
    return {"ok": ok, "key": key, "value": value, "ttl": DEMO_CACHE_TTL}

@app.get("/demo-cache")
def demo_cache_get(key: str = Query(...)):
    val = cache_get(key)
    ttl = cache_ttl(key)
    return {"key": key, "value": val, "ttl": ttl}

# ---- Step 2b: Demo latch (coalescing) endpoint ----
# Simulates an upstream fetch that takes ~1s, but collapses concurrent callers.
# GET /demo-latch?key=quotes:AAPL
@app.get("/demo-latch")
async def demo_latch(key: str = Query(...)):
    """
    Pattern:
      - try to acquire latch for the resource key
      - if acquired: do 'the work' (simulate ~1s upstream), write result to cache
      - if not acquired: wait until latch disappears, then return cached result
    Result is cached for 30s.
    """
    rkey = f"fs:demo:{key}"
    lkey = latch_key_for(rkey)

    # If cached, fast-path
    existing = cache_get(rkey)
    if existing is not None:
        return {"source": "cache", "key": key, "value": existing, "ttl": cache_ttl(rkey)}

    # Try to acquire the latch
    if latch_acquire(lkey, DEMO_LATCH_TTL):
        # We are the leader — simulate upstream work
        await asyncio.sleep(1.0)  # pretend network+compute
        value = f"payload_for_{key}_{int(time.time())}"
        cache_set(rkey, value, DEMO_CACHE_TTL)
        # latch auto-expires in ~5s
        return {"source": "upstream", "key": key, "value": value, "ttl": DEMO_CACHE_TTL}
    else:
        # Someone else is doing the work; wait for latch to clear
        await wait_for_latch_release(lkey, timeout=6.0)
        # Then read the cache (might still be missing if leader failed)
        value = cache_get(rkey)
        return {"source": "coalesced", "key": key, "value": value, "ttl": cache_ttl(rkey)}
