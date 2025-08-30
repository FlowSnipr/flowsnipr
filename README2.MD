
---

# Flow Snipr (README2)

This file continues from the original README and documents all progress made **after the end of Phase 0 work yesterday**.

---

## Current Progress (Phase 0: Foundations, Continued)

### Backend (FastAPI)

**Database & Migrations**

* Added SQLAlchemy `Stock` model (`models.py`).
* Integrated Alembic for database migrations:

  * Baseline migration created.
  * Migration applied successfully, schema verified against Postgres.

**API Health Check**

* Confirmed `/health` endpoint returns `{ "status": "ok" }`.

---

### Frontend (Next.js + Tailwind)

**Bootstrap**

* New app scaffolded via:

  ```powershell
  npx create-next-app@latest web --typescript --eslint --tailwind --app --no-src-dir --use-npm
  ```
* Verified local dev server running at:
  [http://localhost:3000](http://localhost:3000)

**Demo Page (`/demo`)**

* Added chart + grid demo:

  * **Lightweight Charts** integration (live area/line series).
  * **AG Grid** integration (dummy table data).
* Fixed AG Grid v34 theming migration (removed old CSS, applied correct theme props).
* Updated Lightweight Charts code for v5 API changes (`addSeries({ type: "Line" })`).

**API Fetch**

* Frontend calls backend `/health` to display API status.
* Added `web/.env.local`:

  ```env
  NEXT_PUBLIC_API_BASE=http://localhost:8000
  ```

---

### Project Hygiene & Tooling

**Frontend (web)**

* Configured **Prettier** with Tailwind plugin:

  * `.prettierrc` + `.prettierignore` added.
* ESLint configured and verified.
* Added npm scripts:

  * `npm run format` → Prettier write.
  * `npm run lint` → ESLint check.

**Backend (api)**

* Configured **Black** (formatter) + **isort** (import sorter).
* Verified formatting works:

  ```powershell
  .\.venv\Scripts\python -m black .
  .\.venv\Scripts\python -m isort .
  ```

**Pre-commit Hooks (Husky + lint-staged)**

* Set up Husky hooks in `web/.husky/`.
* Pre-commit now runs:

  * Prettier + ESLint (web)
  * Black + isort (api)
* Ensures no unformatted code can be committed.

**Root-level Unified Scripts**
Added `package.json` at repo root with unified commands:

```json
{
  "name": "flowsnipr-root",
  "private": true,
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

Now you can:

* `npm run format:all` → Auto-format frontend + backend.
* `npm run lint:all` → Lint both without writing changes.
* Pre-commit hook runs these automatically.

**Git Hygiene**

* `.gitignore` updated for `.venv`, `__pycache__`, etc.
* Git warnings about LF/CRLF noted, but harmless on Windows.

---

## Updated Project Structure

```
flowsnipr/
├── api/                # FastAPI backend
│   ├── main.py         # FastAPI app w/ /health + Celery integration
│   ├── celery_app.py   # Celery config + hello_task
│   ├── models.py       # SQLAlchemy Stock model
│   ├── alembic/        # Database migrations
│   └── .venv/          # Python virtual environment (ignored in Git)
├── web/                # Next.js frontend
│   ├── app/            # App Router pages
│   ├── .prettierrc     # Prettier config
│   ├── .prettierignore
│   └── ...
├── docker-compose.yml  # Services (Postgres + Redis)
├── package.json        # Root scripts (format:all, lint:all)
└── README2.md          # This file (progress after README.md)
```

---

## How to Run (Recap)

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
* **Pre-commit hook:**
  Auto-runs Prettier/ESLint (frontend) + Black/isort (backend).

---

## Next Steps

* Add `.env` config for DB + Redis secrets.
* Spin up Postgres and confirm connection from FastAPI.
* Add `/stocks` API endpoint and seed test data.
* Hook frontend AG Grid table up to real `/stocks` API.
* Deploy stack (Vercel frontend + backend container).

---

Would you like me to also **merge README.md + README2.md into one continuous doc** once Phase 0 is fully wrapped, so you’ll have a single authoritative README before you move into Phase 1?
