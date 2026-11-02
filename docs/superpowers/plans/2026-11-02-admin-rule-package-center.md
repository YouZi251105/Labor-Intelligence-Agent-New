# Admin Rule Package Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persisted rule package versions, review/publish workflows, runtime published-version loading, and an admin rule package center.

**Architecture:** A `RulePackage` database model stores validated workflow JSON and lifecycle state. Admin APIs validate against `WorkflowRulePackage`, enforce status transitions, and publish immutable versions. The workflow route loads the latest published package with bundled fallback. A focused Vue component provides import, edit, validation, review, and publishing.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, Vue 3, TypeScript.

**Status:** Implementation, lifecycle tests, migration verification, and desktop/mobile browser checks completed.

## Global Constraints

- Only `published` packages affect normal users.
- Invalid JSON or invalid rule references must never be saved as draft.
- Published packages cannot be edited.
- Use the existing `WorkflowRulePackage` schema.
- No Excel or AI-assisted import in this phase.

---

### Task 1: Persistence and Schema

**Files:**
- Create: `backend/app/models/rule_package.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/rule_package.py`
- Create: `backend/alembic/versions/rule_packages_v1.py`
- Test: `backend/tests/test_rule_package_admin.py`

- [ ] Write failing tests for admin listing, import, validation, and lifecycle.
- [ ] Add the model, schemas, seed package, and migration.
- [ ] Run focused tests.

### Task 2: Validation and Lifecycle Service

**Files:**
- Create: `backend/app/services/rule_package_admin.py`
- Create: `backend/app/routes/admin_rule_packages.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] Implement canonical checksum, schema validation summary, and status transition errors.
- [ ] Enforce admin-only access and audit logs.
- [ ] Test invalid imports and invalid transitions.

### Task 3: Runtime Published Package

**Files:**
- Modify: `backend/app/routes/workflow.py`
- Modify: `backend/app/services/rule_packages.py`
- Test: `backend/tests/test_rule_package_admin.py`

- [ ] Publish a distinct version in tests.
- [ ] Confirm normal workflow uses it and retiring restores bundled fallback.

### Task 4: Admin UI

**Files:**
- Create: `frontend/src/components/RulePackageCenter.vue`
- Modify: `frontend/src/views/AdminDashboardView.vue`
- Modify: `frontend/src/layouts/AppLayout.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/styles/base.css`

- [ ] Add `packages` route and sidebar item.
- [ ] Build package list, JSON editor, validation preview, lifecycle actions, template download, and file import.
- [ ] Verify desktop and mobile layouts.

### Task 5: Documentation and Verification

**Files:**
- Modify: `docs/api/接口契约_v1.md`
- Modify: `docs/api/API概览.md`
- Modify: `docs/api/openapi.v1.json`
- Modify: `docs/product/当前功能与边界.md`

- [ ] Export OpenAPI.
- [ ] Run backend tests, Ruff, and Mypy.
- [ ] Run frontend tests, typecheck, build, and focused Playwright.
- [ ] Commit, push, deploy, and verify public behavior.
