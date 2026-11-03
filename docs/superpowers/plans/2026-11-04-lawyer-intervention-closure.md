# Lawyer Intervention Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the first functional lawyer-intervention loop without finalizing legal content or operational metrics.

**Architecture:** Reuse `LawyerRequest`, `CaseReview`, `Document`, and `Case.classification`. Add recommendation metadata to the AI result, special follow-up actions, a case-level resolution decision, and a reviewed-document gate.

**Tech Stack:** FastAPI, Pydantic, Vue 3, TypeScript, pytest, Vitest, Playwright.

## Global Constraints

- Legal content and formal rule values remain pending manual review.
- Users must explicitly choose self-service or lawyer assistance.
- A draft may still be generated before review.
- Only a reviewed `ready_to_file` case may mark a latest document version as ready.
- AI may recommend lawyer intervention but may not assign a lawyer without user or admin action.

---

### Task 1: AI Intervention Recommendation and Actions

**Files:**
- Modify: `backend/app/services/ai.py`
- Modify: `backend/app/schemas/case.py`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/views/WorkspaceView.vue`
- Modify: `frontend/src/styles/base.css`
- Test: `backend/tests/test_ai_followups.py`
- Test: `frontend/src/utils/followUps.test.ts`
- Test: `frontend/e2e/demo-flow.spec.ts`

**Interfaces:**
- Produces: `InterventionRecommendation { recommended, level, reasons, action }`.
- Extends: `FollowUpOption.kind` with `lawyer_request` and `filing_review`.
- Produces: workspace routes to `/cases/{id}?tab=lawyer&request=1` and `/cases/{id}?tab=lawyer&review=1`.

- [x] Add failing backend recommendation tests.
- [x] Add failing frontend parsing and action-routing tests.
- [x] Implement recommendation rules and special follow-up actions.
- [x] Add the always-available lawyer intervention action to the consultation window.
- [x] Verify desktop and mobile interactions.

### Task 2: Final Resolution Confirmation

**Files:**
- Modify: `backend/app/routes/lawyer_service.py`
- Modify: `backend/app/schemas/lawyer_service.py`
- Modify: `frontend/src/views/CaseDetailView.vue`
- Test: `backend/tests/test_lawyer_service.py`

**Interfaces:**
- Produces: `POST /lawyer-service/cases/{case_id}/resolution`.
- Stores: `classification.resolution_decision` and `classification.resolution_confirmed_at`.

- [x] Add failing endpoint and review-decision synchronization tests.
- [x] Implement the case resolution endpoint.
- [x] Add self-service, lawyer-assistance, and pause choices to the case overview.

### Task 3: Formal Document Gate

**Files:**
- Modify: `backend/app/routes/documents.py`
- Modify: `frontend/src/views/CaseDetailView.vue`
- Test: `backend/tests/test_demo_flow.py`

**Interfaces:**
- Produces: `POST /cases/{case_id}/documents/{document_id}/mark-ready`.
- Requires: latest document version and reviewed `ready_to_file` case review.

- [x] Add failing tests for unreviewed and reviewed document readiness.
- [x] Implement the latest-version and review checks.
- [x] Show document status and readiness action in the documents tab.
- [x] Run complete backend, frontend, build, and E2E verification.
