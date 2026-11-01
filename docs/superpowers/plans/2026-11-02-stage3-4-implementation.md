# Stage 3 and Stage 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the planned service-closure features and production-hardening baseline while keeping the application runnable without external services.

**Architecture:** Keep the modular FastAPI monolith and Vue SPA. Add stage 3 domain modules for simulation, lawyer collaboration, help resources, topics, profiles and admin operations. Add stage 4 adapters for storage, asynchronous tasks, migrations, rate limiting, metrics, backup and deployment. Local SQLite filesystem and synchronous task fallbacks remain the default so tests do not require Docker.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic; Vue 3, TypeScript, Vite, Pinia, Element Plus, Lucide; Pytest, Vitest, Playwright; PostgreSQL, Redis/Celery, MinIO/S3 and Nginx targets.

## Global Constraints

- Do not invent legal rules, deadlines, citations or document templates.
- Legal rules remain imported drafts until the legal content owner approves them.
- AI output is advisory and never changes case stage directly.
- Every new endpoint checks case ownership, lawyer assignment or admin role.
- Error responses use `{"detail": "..."}`.
- New API fields are additive in v1.
- Local tests must run without Docker, an external AI key, PostgreSQL, Redis or MinIO.
- Real infrastructure checks that cannot run locally must be recorded as unverified.
- Each task must pass its focused tests before the next task starts.

---

## Stage 3: Service Closure

### Task 1: Stage 3 Contract and Collaboration Models

**Files:**
- Create: `backend/app/models/collaboration.py`
- Create: `backend/app/schemas/simulation.py`
- Create: `backend/app/schemas/collaboration.py`
- Create: `backend/app/schemas/profile.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `docs/api/接口契约_v1.md`
- Test: `backend/tests/test_stage3_contract.py`

**Interfaces:**
- `SimulationSession` stores case, user, role, scenario and status.
- `SimulationMessage` stores role, content and structured score JSON.
- `LawyerOpinion` stores case, lawyer, content and review status.
- `ServiceRecord` stores case, lawyer, service type, summary, duration and status.
- `RevenueLedger` stores lawyer, optional case/service record, amount cents, type and status.
- `UserProfile` stores masked identity metadata and verification status.
- `HelpResource` stores arbitration, court, legal-aid and site-lawyer entries.
- `RuleConfig` stores dispute rules with `pending_review` or `approved` status.

- [ ] Write failing tests for table round trips and profile masking.
- [ ] Run `pytest tests/test_stage3_contract.py -q` and confirm failure.
- [ ] Implement models and schemas.
- [ ] Run the focused test and confirm pass.
- [ ] Commit `feat(stage3): add collaboration and service models`.

### Task 2: AI Simulation

**Files:**
- Create: `backend/app/services/simulation.py`
- Create: `backend/app/routes/simulations.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_simulations.py`

**Interfaces:**
- `POST /cases/{case_id}/simulations` creates a session.
- `GET /cases/{case_id}/simulations` lists sessions.
- `GET /cases/{case_id}/simulations/{session_id}` returns messages.
- `POST /cases/{case_id}/simulations/{session_id}/messages` returns role reply and score.
- Score dimensions: `clarity`, `evidence_awareness`, `legal_appropriateness`, `overall`.

- [ ] Write failing endpoint tests for worker ownership, score shape and role rejection.
- [ ] Run focused tests and confirm failure.
- [ ] Implement deterministic demo coaching with optional AI-safe fallback.
- [ ] Run focused tests, Ruff and Mypy.
- [ ] Commit `feat(stage3): add simulation and coaching APIs`.

### Task 3: Lawyer Collaboration

**Files:**
- Create: `backend/app/services/collaboration.py`
- Create: `backend/app/routes/collaboration.py`
- Modify: `backend/app/routes/lawyer.py`
- Modify: `backend/app/routes/admin.py`
- Test: `backend/tests/test_collaboration.py`

**Interfaces:**
- Lawyers create opinions and service records only for assigned cases.
- `GET /lawyer/revenue` returns the authenticated lawyer ledger.
- Admins can list service records and revenue entries.
- Service status transitions are `pending -> in_progress -> completed`.
- Revenue status transitions are `pending -> confirmed -> paid`.
- Every mutation writes an audit event.

- [ ] Write failing permission tests for unassigned lawyers and users.
- [ ] Write failing transition and audit tests.
- [ ] Implement services and endpoints.
- [ ] Run focused tests and static checks.
- [ ] Commit `feat(stage3): add lawyer collaboration ledger`.

### Task 4: Help, Profile, Topics and Admin Operations

**Files:**
- Create: `backend/app/services/help.py`
- Create: `backend/app/routes/help.py`
- Create: `backend/app/routes/profile.py`
- Create: `backend/app/routes/analytics.py`
- Modify: `backend/app/routes/admin.py`
- Modify: `backend/app/services/seed.py`
- Test: `backend/tests/test_help_admin.py`

**Interfaces:**
- `GET /help/resources` returns active public support entries.
- `GET /help/site-lawyers` returns approved active lawyer profiles.
- `GET /analytics/topics` returns aggregated categories only, never raw user messages.
- `GET /analytics/history` returns the authenticated user's compact session history.
- `GET /users/me/profile`, `PUT /users/me/profile`.
- Admin endpoints list materials, audit logs and rules; update lawyer status and rule review status.

- [ ] Write failing privacy tests proving raw messages are not returned by topics.
- [ ] Write failing profile validation and admin permission tests.
- [ ] Seed demo help resources and pending rule configs.
- [ ] Implement endpoints and filters.
- [ ] Run focused tests and static checks.
- [ ] Commit `feat(stage3): add help topics and admin operations`.

### Task 5: Stage 3 Frontend

**Files:**
- Create: `frontend/src/views/SimulationView.vue`
- Create: `frontend/src/views/HelpCenterView.vue`
- Modify: `frontend/src/views/LawyerDashboardView.vue`
- Modify: `frontend/src/views/AdminDashboardView.vue`
- Modify: `frontend/src/views/WorkspaceView.vue`
- Modify: `frontend/src/views/CasesView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/styles/base.css`
- Test: `frontend/e2e/demo-flow.spec.ts`

**Interfaces:**
- Simulation page supports role/scenario selection, messages and score display.
- Help page supports support directory, site lawyers and manual contact entry.
- Lawyer page supports opinions, service records and revenue.
- Admin page supports audit, rules, materials and lawyer status.
- Case creation supports the six dispute types without legal rule invention.
- History and topic panels default collapsed and use aggregated labels.

- [ ] Add failing Playwright flows for simulation and help center.
- [ ] Run focused E2E and confirm failure.
- [ ] Implement pages, types and states.
- [ ] Run Vitest, typecheck, build and full Playwright.
- [ ] Commit `feat(stage3): deliver service closure UI`.

### Task 6: Stage 3 Acceptance

**Files:**
- Modify: `docs/development/分阶段分工与验收.md`
- Modify: `docs/product/当前功能与边界.md`
- Modify: `当前进度与两人分工_2026-11-01.txt`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/user/用户使用手册.md`
- Modify: `docs/lawyer/律师使用手册.md`
- Modify: `docs/admin/管理员使用手册.md`
- Modify: `docs/demo/演示脚本.md`

- [ ] Export OpenAPI.
- [ ] Run backend tests, Ruff, Mypy.
- [ ] Run frontend tests, typecheck, build and Playwright.
- [ ] Update all documents and mark stage 3 accepted.
- [ ] Merge `integration/stage3` to `main`.
- [ ] Tag `stage-3-accepted`.

---

## Stage 4: Production Baseline

### Task 7: Object Storage Adapter

**Files:**
- Create: `backend/app/services/storage.py`
- Modify: `backend/app/services/evidence.py`
- Modify: `backend/app/routes/evidence.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_storage.py`

**Interfaces:**
- `StorageBackend.save(key, content)`, `read(key)`, `delete(key)`, `exists(key)`.
- `LocalStorage` uses `UPLOAD_DIR`.
- `S3Storage` uses boto3 with MinIO endpoint and bucket.
- `get_storage()` selects `STORAGE_BACKEND=local|s3`.
- Evidence records store an object key, not a client-supplied path.

- [ ] Write failing local storage round-trip and traversal-safety tests.
- [ ] Implement local backend and dependency selection.
- [ ] Refactor evidence upload, retry and download through the adapter.
- [ ] Run focused tests and full backend regression.
- [ ] Commit `feat(stage4): add object storage adapter`.

### Task 8: Asynchronous Extraction and Export

**Files:**
- Create: `backend/app/services/jobs.py`
- Create: `backend/app/workers/tasks.py`
- Modify: `backend/app/workers/celery_app.py`
- Modify: `backend/app/routes/evidence.py`
- Modify: `backend/app/routes/documents.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_jobs.py`

**Interfaces:**
- `enqueue_evidence_extraction(evidence_id)` returns `sync` or Celery task id.
- `enqueue_document_export(document_id, format)` returns bytes in sync mode.
- `TASK_BACKEND=inline|celery`.
- Celery task failures keep the resource and expose a retryable status.

- [ ] Write failing inline task and retry-state tests.
- [ ] Implement inline fallback and Celery task wrappers.
- [ ] Run focused tests and full backend regression.
- [ ] Commit `feat(stage4): add asynchronous task boundary`.

### Task 9: Database Migration and CI

**Files:**
- Create: `backend/alembic/versions/20261102_0001_initial.py`
- Create: `.github/workflows/ci.yml`
- Modify: `backend/alembic/env.py`
- Modify: `backend/app/db/session.py`
- Modify: `README.md`
- Test: `backend/tests/test_migrations.py`

**Interfaces:**
- Initial Alembic revision creates all current metadata tables.
- `alembic upgrade head` is idempotent on an empty database.
- CI runs backend tests/Ruff/Mypy and frontend tests/typecheck/build.

- [ ] Write failing migration smoke test on a temporary SQLite database.
- [ ] Implement migration and CI.
- [ ] Run migration smoke tests twice.
- [ ] Commit `chore(stage4): add migrations and CI`.

### Task 10: Security and Observability

**Files:**
- Create: `backend/app/core/rate_limit.py`
- Create: `backend/app/api/v1/endpoints/metrics.py`
- Create: `backend/app/middleware/request_context.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/logging.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_security_observability.py`

**Interfaces:**
- Requests receive `X-Request-ID`.
- Auth endpoints use a fixed-window limiter.
- `GET /metrics` returns text metrics without personal data.
- Logs include request ID, method, path, status and duration.
- `TRUSTED_HOSTS`, `RATE_LIMIT_PER_MINUTE` and `ENABLE_METRICS` are configurable.

- [ ] Write failing request ID, limiter and metrics tests.
- [ ] Implement middleware and metrics.
- [ ] Run focused tests and full regression.
- [ ] Commit `feat(stage4): add rate limits and observability`.

### Task 11: Backup, Compose and Production Documentation

**Files:**
- Create: `infra/scripts/backup.ps1`
- Create: `infra/scripts/restore.ps1`
- Create: `infra/nginx/https.conf.example`
- Modify: `docker-compose.yml`
- Modify: `backend/Dockerfile`
- Modify: `frontend/Dockerfile`
- Modify: `infra/nginx/default.conf`
- Modify: `README.md`
- Modify: `docs/security/安全与权限说明.md`

**Interfaces:**
- Backup scripts support SQLite and PostgreSQL dump commands.
- Restore scripts require an explicit backup path.
- Compose includes PostgreSQL, Redis, MinIO, backend, Celery, frontend and Nginx.
- HTTPS example documents certificate paths without embedding secrets.

- [ ] Add backup and restore scripts with path validation.
- [ ] Update Compose, Dockerfiles and Nginx examples.
- [ ] Run `docker compose config` if Docker exists; otherwise record unavailable.
- [ ] Commit `chore(stage4): add deployment and recovery assets`.

### Task 12: Frontend Production Polish and Final Acceptance

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/styles/base.css`
- Modify: `frontend/src/layouts/AppLayout.vue`
- Modify: `frontend/e2e/demo-flow.spec.ts`
- Modify: all manuals and demo documents.

- [ ] Lazy-load route views and preserve current visual behavior.
- [ ] Add keyboard focus and reduced-motion checks.
- [ ] Run frontend tests, typecheck, build and Playwright.
- [ ] Run backend tests, Ruff and Mypy.
- [ ] Update stage and operation documentation.
- [ ] Merge `integration/stage4` to `main`.
- [ ] Tag `stage-4-accepted`.

## Environment Limitations

This machine does not currently provide Docker, PostgreSQL, Redis or MinIO executables. Evidence extraction and export task boundaries, migration files, Compose definitions and backup scripts can still be implemented and tested through local fallbacks. Container startup, external-service connectivity and restore-from-real-backup remain deferred checks and must not be reported as verified until they run on a machine with those services.
