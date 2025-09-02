# api/redis_client.py
import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def check_redis() -> None:
    """Raise on failure; used by /healthz."""
    redis_client.ping()
