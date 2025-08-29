Flow Snipr

FlowSnipr

A lightweight “Bloomberg-like” market data & options flow terminal built by a solo developer.
This repo contains both the frontend (Next.js + Tailwind) and backend (FastAPI + Celery + Redis + Postgres).

Current Progress (Phase 0: Foundations)

Repo Setup
Project initialized with GitHub, cloned locally into flowsnipr/.
Backend lives in api/ (FastAPI).
Frontend (Next.js) will live in web/ (coming soon).

Backend (FastAPI)
Skeleton API running at uvicorn main:app --reload --port 8000.
/health endpoint returns { "status": "ok" }.

Background Tasks (Celery + Redis)
Redis container running via Docker (redis://localhost:6379/0).
Celery worker connected to Redis.
Sample hello_task works end-to-end:

Trigger: POST /tasks/hello?name=FlowSnipr

Check status: GET /tasks/status/{task_id}

Returns: "hello FlowSnipr"

Infrastructure
Docker Compose prepared for Postgres + Redis.
Local dev environment: Python 3.11+, Node.js, Docker Desktop.

Project Structure

flowsnipr/
├── api/ # FastAPI backend
│ ├── main.py # FastAPI app w/ /health + Celery integration
│ ├── celery_app.py # Celery config + hello_task
│ └── .venv/ # Python virtual environment (ignored in Git)
├── web/ # Next.js frontend (to be created in Phase 1)
├── docker-compose.yml # Services (Postgres + Redis)
└── README.md # This file

How to Run (So Far)

Backend (FastAPI)
cd api
..venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
Check: http://127.0.0.1:8000/health

Celery Worker
cd api
..venv\Scripts\Activate.ps1
celery -A celery_app.celery_app worker -l info -P solo

Redis (Docker)
docker compose up -d

Test Task
Trigger:
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/tasks/hello?name=FlowSnipr
"

Check status:
Invoke-RestMethod -Uri "http://127.0.0.1:8000/tasks/status/{task_id}
"

Next Steps

Add .env config for DB + Redis secrets.

Spin up Postgres and test connection from FastAPI.

Initialize migrations (Alembic).

Bootstrap frontend in /web/ with Next.js + Tailwind.

Connect frontend to backend /health for first API fetch.
