# Workflow Block Designer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add constrained visual workflow blocks, graph validation, node/stage decoupling, and a drag-and-drop admin designer.

**Architecture:** Designer metadata is embedded in the canonical workflow package. Pydantic validates block types, ports, conditions, and reachability. The runtime uses `workflow_node_id` for the active block and `Case.stage` for the business stage. Vue provides palette, canvas, inspector, and JSON synchronization.

**Tech Stack:** Pydantic 2, FastAPI, SQLAlchemy JSON, Vue 3, TypeScript.

**Status:** Core implementation and desktop/mobile browser verification completed.

## Global Constraints

- Content users cannot create arbitrary block types.
- End blocks cannot have outputs.
- Gates require both pass and fallback paths.
- Runtime never evaluates user-provided code or expressions.
- Existing rule packages without designer metadata remain compatible.

---

### Task 1: Designer Schema and Tests

**Files:**
- Modify: `backend/app/schemas/workflow_rules.py`
- Create: `backend/tests/test_workflow_designer.py`

- [ ] Validate block coverage, gate ports, end blocks, and reachability.
- [ ] Preserve packages without designer metadata.

### Task 2: Runtime Node/Stage Split

**Files:**
- Modify: `backend/app/services/workflow.py`
- Modify: `backend/app/routes/workflow.py`

- [ ] Read `workflow_node_id` from case classification.
- [ ] Persist target node on transition.
- [ ] Derive business stage from the selected node.

### Task 3: Visual Designer

**Files:**
- Create: `frontend/src/components/WorkflowBlockDesigner.vue`
- Modify: `frontend/src/components/RulePackageCenter.vue`
- Modify: `frontend/src/styles/base.css`

- [ ] Add controlled palette, canvas, drag positioning, inspector, and connection selection.
- [ ] Synchronize visual state with JSON.
- [ ] Keep non-editable versions read-only.

### Task 4: Documentation and Verification

**Files:**
- Modify: `docs/api/接口契约_v1.md`
- Modify: `docs/api/openapi.v1.json`
- Modify: `docs/product/当前功能与边界.md`

- [ ] Export OpenAPI.
- [ ] Run backend/frontend suites.
- [ ] Run desktop/mobile Playwright.
- [ ] Commit, push, deploy, and verify.
