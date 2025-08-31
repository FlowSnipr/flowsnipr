
---

# Flow Snipr (README2)

This file continues from the original README and documents all progress made **after the end of Phase 0 work yesterday**.

---

## Current Progress (Phase 0: Foundations, Completed)

### Backend (FastAPI + Celery + Redis)

**Database & Migrations**

* SQLAlchemy `Stock` model (`models.py`) created.
* Alembic initialized, baseline migration generated and applied successfully.
* Verified schema exists in Postgres.

**API Health & Utility Endpoints**

* `/health` → returns `{ "status": "ok" }`.
* `/env-test` → confirms environment variables loaded correctly.
* `/ping/db` → verifies Postgres connectivity with `SELECT 1`.

**Stocks API**

* `/stocks` (POST) → create stock record.
* `/stocks` (GET) → list stocks (ordered).

**Celery + Redis Task Pipeline**

* `/tasks/hello` → kicks async task via Celery.
* `/tasks/status/{task_id}` → polls task result/state.
* Confirmed working:

  * Task queued and processed by Celery worker.
  * Returns `"SUCCESS"` with payload `"hello FlowSnipr"`.

---

### Frontend (Next.js + Tailwind)

**Bootstrap**

* Next.js 15 app scaffolded (`web/`).
* Local dev server verified at [http://localhost:3000](http://localhost:3000).

**Demo Page (`/demo`)**

* Chart + grid proof-of-concept:

  * **Lightweight Charts v5** rendering synthetic line/area data.
  * **AG Grid v34** rendering dummy rows.
* Theming migration fixed (dropped legacy CSS, used new `theme` API).
* Chart API updated to v5 (`addSeries({ type: "Line" })`).

**API Fetch**

* Frontend fetches backend `/health` and displays API status.
* Configured `web/.env.local`:

  ```env
  NEXT_PUBLIC_API_BASE=http://localhost:8000
  ```

---

### Project Hygiene & Tooling

**Frontend (web)**

* Configured Prettier + Tailwind plugin (`.prettierrc`, `.prettierignore`).
* ESLint configured and passing cleanly.
* Scripts added:

  * `npm run format` → Prettier write.
  * `npm run lint` → ESLint check.

**Backend (api)**

* Configured **Black** + **isort**.
* Verified formatting with manual + automated runs.

**Pre-commit Hooks (Husky + lint-staged)**

* Pre-commit hook added at `web/.husky/pre-commit`.
* Runs on commit:

  * Prettier + ESLint (web).
  * Black + isort (api).

**Root-level Unified Scripts**

* Added `package.json` at repo root with unified commands:

  ```json
  {
    "scripts": {
      "format:web": "npm --prefix web run format && npm --prefix web run lint -- --fix",
      "format:api": "cd api && .\\.venv\\Scripts\\python -m black . && .\\.venv\\Scripts\\python -m isort .",
      "format:all": "npm run format:web && npm run format:api",
      "lint:web": "npm --prefix web run lint",
      "lint:api": "cd api && .\\.venv\\Scripts\\python -m black --check . && .\\.venv\\Scripts\\python -m isort --check-only .",
      "lint:all": "npm run lint:web && npm run lint:api"
    }
  }
  ```
* Now you can:

  * `npm run format:all` → auto-format frontend + backend.
  * `npm run lint:all` → lint both without writing changes.
  * Pre-commit hook enforces these automatically.

**Git Hygiene**

* `.gitignore` updated (e.g., `.venv`, `__pycache__`).
* CRLF warnings noted (Windows), but harmless.

---

## Updated Project Structure

```
flowsnipr/
├── api/                # FastAPI backend
│   ├── main.py         # FastAPI app (health, stocks, celery tasks)
│   ├── celery_app.py   # Celery config + hello_task
│   ├── models.py       # SQLAlchemy Stock model
│   ├── alembic/        # Database migrations
│   └── .venv/          # Python virtual environment (ignored in Git)
├── web/                # Next.js frontend
│   ├── app/            # App Router pages (includes /demo)
│   ├── .prettierrc     # Prettier config
│   ├── .prettierignore
│   └── ...
├── docker-compose.yml  # Services (Postgres + Redis)
├── package.json        # Root scripts (format:all, lint:all)
└── README2.md          # This file (progress after README.md)
```

---

## How to Run

### Backend

```powershell
cd api
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Celery Worker

```powershell
cd api
.\.venv\Scripts\Activate.ps1
celery -A celery_app.celery_app worker -l info -P solo
```

### Redis

```powershell
docker compose up -d
```

### Frontend

```powershell
cd web
npm run dev
```

Check: [http://localhost:3000/demo](http://localhost:3000/demo)

---

## Developer Workflow

* **Format everything:**

  ```powershell
  npm run format:all
  ```
* **Lint everything:**

  ```powershell
  npm run lint:all
  ```
* **Pre-commit hook:** auto-runs Prettier/ESLint (frontend) + Black/isort (backend).

---

## Phase 0 ✅ Completed

We now have:

* Backend (FastAPI) connected to Postgres with migrations, models, and test endpoints.
* Celery/Redis async task pipeline working end-to-end.
* Frontend demo page rendering chart + grid and fetching API health.
* Unified formatting + linting automation across stack.
* Pre-commit hook enforcing hygiene.

---

## Next Steps (Phase 1)

* Add `.env` configs for DB + Redis (shared across frontend/backend).
* Seed Postgres with example stocks (MSFT, AAPL, TSLA).
* Add `/stocks/{symbol}` endpoint for single-stock fetch.
* Add dummy `/options` endpoint (hardcoded options chain JSON).
* Hook frontend AG Grid table to real `/stocks` API.
* Replace chart with API-driven timeseries.
* Dockerize backend (uvicorn, celery, redis) with dev override.
* Deploy stack (Vercel frontend + Render/Fly backend).

---

