# api/db.py
import os
from sqlalchemy import create_engine, text

# If you're running FastAPI on your host and Postgres via docker-compose,
# "localhost:5432" is correct. If you later dockerize the API, you'll swap to "db:5432".
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres",
)

# pool_pre_ping avoids stale connections
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

def check_db() -> None:
    """Raise on failure; used by /healthz."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
