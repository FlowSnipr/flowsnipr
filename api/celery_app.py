# api/celery_app.py
import os
import json
from datetime import datetime, timezone
from random import random, choice

from celery import Celery
from dotenv import load_dotenv
import redis

load_dotenv()  # loads .env next to this file if present

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "flowsnipr",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# ---- NEW: redis client for tasks ----
_r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ---- OPTIONAL nicety (not required) ----
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.timezone = "UTC"

@celery_app.task
def hello_task(name: str = "world"):
    return f"hello {name}"

# ---- NEW: mock generators ----
def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _mock_tape(n=6):
    # pretend this is a live tape of interesting prints
    syms = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META"]
    arr = []
    for _ in range(n):
        sym = choice(syms)
        side = choice(["C", "P"])
        arr.append({
            "t": _now_iso(),
            "symbol": sym,
            "type": "opt",
            "side": side,
            "strike": round(50 + 500 * random(), 2),
            "expiry": "2025-12-19",
            "prem": round(10_000 * random(), 2),
        })
    return arr

def _mock_hotset(n=8):
    syms = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "SPY", "QQQ"]
    return [{
        "symbol": s,
        "score": round(50 + 50 * random(), 2),
        "updated": _now_iso(),
    } for s in syms[:n]]

# ---- NEW: scheduled tasks that write to Redis ----
@celery_app.task
def refresh_tape():
    payload = _mock_tape()
    _r.set("fs:tape", json.dumps(payload), ex=180)  # TTL 3m
    # return for logs
    return {"wrote": len(payload), "key": "fs:tape", "at": _now_iso()}

@celery_app.task
def refresh_hotset():
    payload = _mock_hotset()
    _r.set("fs:hotset", json.dumps(payload), ex=180)  # TTL 3m
    return {"wrote": len(payload), "key": "fs:hotset", "at": _now_iso()}

# ---- NEW: beat schedule ----
celery_app.conf.beat_schedule = {
    "refresh_tape_every_30s": {
        "task": "celery_app.refresh_tape",
        "schedule": 30.0,
    },
    "refresh_hotset_every_60s": {
        "task": "celery_app.refresh_hotset",
        "schedule": 60.0,
    },
}
