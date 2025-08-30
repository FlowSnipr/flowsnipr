import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()  # loads .env next to this file if present

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "flowsnipr",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

@celery_app.task
def hello_task(name: str = "world"):
    return f"hello {name}"
