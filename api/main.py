from fastapi import FastAPI
from celery.result import AsyncResult
from dotenv import load_dotenv
import os

from celery_app import celery_app, hello_task

# SQLAlchemy imports
from sqlalchemy import create_engine, text, Column, Integer, String
from sqlalchemy.orm import Session, declarative_base

# Load environment variables from api/.env
load_dotenv(override=True)

# --- Database setup ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base = declarative_base()

# --- Example table ---
class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)

# --- FastAPI app ---
app = FastAPI()

@app.on_event("startup")
def on_startup():
    # Create tables automatically on startup if missing
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

# ---- ENV TEST ----
@app.get("/env-test")
def env_test():
    return {
        "POSTGRES_USER": os.getenv("POSTGRES_USER"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
        "REDIS_URL": os.getenv("REDIS_URL"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
    }

# ---- Database connectivity test ----
@app.get("/ping/db")
def ping_db():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return {"db_connected": bool(result)}
    except Exception as e:
        return {"db_connected": False, "error": str(e)}

# ---- Stocks endpoints ----
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

# ---- Celery demo endpoints ----
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
