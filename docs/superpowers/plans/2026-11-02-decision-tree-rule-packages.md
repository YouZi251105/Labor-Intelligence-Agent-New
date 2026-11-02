# Decision Tree and Rule Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a config-driven decision tree with versioned rule packages, path selection, and reviewed deadline hints.

**Architecture:** A typed Pydantic rule package is loaded from an internal JSON file. The workflow service evaluates node options and conditions while preserving the existing stage-based API. The Vue case overview renders option outcomes and pending-review deadline hints.

**Tech Stack:** FastAPI, Pydantic 2, SQLAlchemy JSON classification, Vue 3, TypeScript, Vitest, Playwright.

**Status:** Implementation and local browser verification completed.

## Global Constraints

- Keep existing workflow endpoints and old `target_stage` requests compatible.
- Do not hardcode legal branch content in service functions.
- Built-in rules stay `pending_review`.
- Unreviewed deadlines never produce official due dates.
- Do not implement admin editing or Excel import in this phase.

---

### Task 1: Rule Package Schema and Content

**Files:**
- Create: `backend/app/schemas/workflow_rules.py`
- Create: `backend/app/content/workflow_rules.v1.json`
- Create: `backend/app/services/rule_packages.py`
- Test: `backend/tests/test_workflow_rules.py`

**Interfaces:**
- Produces: `WorkflowRulePackage`, `load_default_workflow_package()`

- [ ] Write tests validating the built-in package and rejecting a missing target node.
- [ ] Run tests and confirm they fail because the schema and loader do not exist.
- [ ] Add Pydantic models, JSON content, and cached loader.
- [ ] Run tests and confirm they pass.

### Task 2: Decision Tree Evaluation

**Files:**
- Modify: `backend/app/schemas/workflow.py`
- Modify: `backend/app/services/workflow.py`
- Test: `backend/tests/test_workflow.py`

**Interfaces:**
- Produces: `build_workflow(case, evidence_items, package=None) -> WorkflowResponse`

- [ ] Add failing tests for multiple intake options, stage gating, deadline review state, and package metadata.
- [ ] Run focused tests and confirm the new response fields are missing.
- [ ] Implement condition evaluation and response mapping from the rule package.
- [ ] Run focused tests and confirm they pass.

### Task 3: Transition API and Path Persistence

**Files:**
- Modify: `backend/app/schemas/workflow.py`
- Modify: `backend/app/routes/workflow.py`
- Test: `backend/tests/test_workflow.py`

**Interfaces:**
- Consumes: rule option `id`, `target_stage`, `enabled`
- Produces: persisted `Case.classification.workflow_choices`

- [ ] Add failing tests for `option_id`, legacy `target_stage`, persisted path, and invalid option.
- [ ] Run focused tests and confirm they fail.
- [ ] Resolve options on the server and persist selection metadata.
- [ ] Run focused tests and confirm they pass.

### Task 4: Frontend Types and Workflow UI

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/views/CaseDetailView.vue`
- Modify: `frontend/src/styles/base.css`

**Interfaces:**
- Consumes: extended `WorkflowResponse`
- Produces: option cards with outcome, next step, deadline hints, review badge

- [ ] Update TypeScript types first and run typecheck to expose template errors.
- [ ] Render all options with unique keys and `option_id` transitions.
- [ ] Add restrained styles and mobile layout.
- [ ] Run typecheck, unit tests, and build.

### Task 5: Documentation and Verification

**Files:**
- Modify: `docs/api/接口契约_v1.md`
- Modify: `docs/api/openapi.v1.json`
- Modify: `docs/product/当前功能与边界.md`
- Modify: `docs/README.md` if a new document link is needed.

**Interfaces:**
- Produces: synchronized workflow contract and current capability description.

- [ ] Update API documentation and OpenAPI.
- [ ] Run backend pytest, Ruff, and Mypy.
- [ ] Run frontend tests, typecheck, and build.
- [ ] Run focused Playwright workflow coverage against the validation environment after deployment.
- [ ] Commit and push.
