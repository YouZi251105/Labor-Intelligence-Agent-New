# Lawyer Service and Evidence Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the authorization and state-machine gaps in the newly merged lawyer service, then connect evidence-image authenticity screening to the real upload flow.

**Architecture:** Keep the existing FastAPI modular monolith and Vue views. Add explicit state transitions and object-level authorization checks in `lawyer_service.py`; invoke the existing `evidence_forensics` service before storing an image and persist a non-authoritative screening summary in `Evidence.assessment`.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, pytest, Vue 3, TypeScript, Vitest.

## Global Constraints

- Do not claim the screening result is a forensic authenticity conclusion.
- Preserve the existing public API and add fields only when backward compatible.
- All sensitive object access must be verified against the case owner, assigned lawyer, or administrator.
- Legal content remains pending manual review.
- Use TDD: add a failing test before production code for every behavior change.

---

### Task 1: Lawyer Service State and Authorization Fixes

**Files:**
- Modify: `backend/app/routes/lawyer_service.py`
- Modify: `backend/app/routes/cases.py`
- Test: `backend/tests/test_lawyer_service.py`
- Test: `backend/tests/test_cases_archive_delete.py`

**Interfaces:**
- Consumes: `LawyerRequest`, `ConsultationSession`, `CaseReview`, `Case.assigned_lawyer_id`.
- Produces: `in_session` request status after the first successful message; `completed` status after closing; `404` for a lawyer cancelling another user's request; `409` when a non-owner lawyer submits a review for an already assigned case.

- [ ] Add failing tests for first-message status transition, session close, cancellation authorization, review assignment conflict, and case deletion with lawyer-service records.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Implement the minimal route changes.
- [ ] Run the focused tests and the complete backend suite.
- [ ] Commit the backend fix.

### Task 2: User-Facing Rejection and Session Status

**Files:**
- Modify: `frontend/src/views/CaseDetailView.vue`
- Modify: `frontend/src/styles/base.css`
- Test: `frontend/e2e/demo-flow.spec.ts`

**Interfaces:**
- Consumes: lawyer request `status`, `reject_reason`, `created_at`.
- Produces: a visible terminal-request summary so rejected and cancelled requests retain their reason; the active form remains available for a new request.

- [ ] Add a Playwright assertion for a rejected request reason remaining visible after the request becomes terminal.
- [ ] Run the focused Playwright test and confirm it fails.
- [ ] Add the terminal-request presentation without changing the backend contract.
- [ ] Run frontend unit tests, typecheck, build, and the focused E2E test.
- [ ] Commit the frontend fix.

### Task 3: Evidence Image Authenticity Screening

**Files:**
- Modify: `backend/app/routes/evidence.py`
- Modify: `backend/app/schemas/evidence.py`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/views/CaseDetailView.vue`
- Modify: `docs/api/接口契约_v1.md`
- Modify: `docs/product/当前功能与边界.md`
- Test: `backend/tests/test_evidence_forensics.py`
- Test: `backend/tests/test_demo_flow.py`

**Interfaces:**
- Consumes: `analyze_image(filename, content) -> ForensicsResult`.
- Produces: accepted image evidence contains `assessment.forensics = {image_type, suspicious, reasons, checks, disclaimer}`; a suspicious image upload returns `422` with a `detail` string and is not stored.

- [ ] Add failing API tests for accepted image metadata and rejected suspicious images.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Invoke screening before storage and persist accepted results.
- [ ] Add a visible image screening status in the evidence card.
- [ ] Update the contract and product boundary documents.
- [ ] Run backend, frontend, typecheck, build, and relevant E2E tests.
- [ ] Commit the evidence-screening feature.

