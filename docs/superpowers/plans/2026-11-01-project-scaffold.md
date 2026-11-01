# Labor Intelligence Agent Project Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Initialize a clean, runnable Vue 3 + FastAPI monorepo for the first development milestone.

**Architecture:** A modular monolith split into `frontend`, `backend`, `infra`, and `docs`. The backend exposes a versioned health API and pre-configures database, queue, object storage, and settings boundaries. The frontend provides a responsive legal-service workspace shell with a light red-and-white visual system.

**Tech Stack:** Vue 3, TypeScript, Vite, Pinia, Vue Router, Element Plus, Lucide icons; Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Redis, Celery, PostgreSQL/pgvector, MinIO; Pytest, Vitest, Playwright-ready configuration.

## Global Constraints

- Keep the project self-contained and independently deployable.
- The new project root is `Labor-Intelligence-Agent`.
- Initial product scope is Chinese law and Chinese language only.
- Use a light legal-service visual theme; no dark-dominant interface.
- Keep the first milestone to framework initialization, not complete legal workflows.
- All secrets enter through environment variables and never source files.

---

### Task 1: Root Repository and Infrastructure

**Files:**
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `.env.example`
- Create: `README.md`
- Create: `docker-compose.yml`
- Create: `infra/nginx/default.conf`

**Interfaces:**
- Produces: documented local-development commands and environment keys.
- Produces: service names `db`, `redis`, `minio`, `backend`, `worker`, `frontend`.

- [ ] **Step 1: Create root repository metadata and environment examples**
- [ ] **Step 2: Add Docker Compose services for PostgreSQL/pgvector, Redis, MinIO, FastAPI, Celery, and Vue/Nginx**
- [ ] **Step 3: Add Nginx API proxy configuration**
- [ ] **Step 4: Verify no source file contains a real secret**

### Task 2: Backend Application Skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/app/api/v1/router.py`
- Create: `backend/app/api/v1/endpoints/health.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/workers/celery_app.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/Dockerfile`

**Interfaces:**
- Produces: `GET /api/v1/health` returning `{status, service, version, environment}`.
- Produces: `get_settings()` and `get_engine()` boundaries for later modules.

- [ ] **Step 1: Write the failing health endpoint test**
- [ ] **Step 2: Run it and confirm the app module is missing**
- [ ] **Step 3: Implement configuration, logging, API router, and health endpoint**
- [ ] **Step 4: Run backend tests and ruff checks**

### Task 3: Vue Frontend Workspace Shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/AppLayout.vue`
- Create: `frontend/src/views/WorkspaceView.vue`
- Create: `frontend/src/views/ModulePlaceholderView.vue`
- Create: `frontend/src/stores/workspace.ts`
- Create: `frontend/src/api/http.ts`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/base.css`
- Create: `frontend/src/utils/format.ts`
- Create: `frontend/src/utils/format.test.ts`

**Interfaces:**
- Produces: user routes `/`, `/cases`, `/evidence`, `/simulation`, `/help`.
- Produces: `apiGet<T>()` client using `/api/v1`.
- Produces: workspace backend status display using the health endpoint.

- [ ] **Step 1: Create Vue application and route shell**
- [ ] **Step 2: Implement the light legal-service design tokens and responsive layout**
- [ ] **Step 3: Add backend connectivity status and placeholder module routes**
- [ ] **Step 4: Run Vitest, typecheck, and production build**

### Task 4: End-to-End Verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: backend and frontend commands from earlier tasks.
- Produces: a verified project scaffold with documented limitations.

- [ ] **Step 1: Install backend and frontend dependencies**
- [ ] **Step 2: Run backend tests and frontend checks**
- [ ] **Step 3: Start both development servers and smoke-test the API**
- [ ] **Step 4: Record unavailable checks, including Docker validation when Docker is absent**
