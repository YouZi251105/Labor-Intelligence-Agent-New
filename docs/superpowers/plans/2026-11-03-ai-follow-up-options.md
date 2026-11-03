# AI Follow-up Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the AI consultation's final suggestion sentence into structured, clickable follow-up options, and make role simulation use the configured Qwen model with a deterministic fallback.

**Architecture:** Extend the existing AI result contract with `follow_up_options`. Qwen may emit a delimited JSON list of suggested questions; the backend strips that block from user-visible text, validates at most four entries, and merges them with locally derived information-completion actions. Vue renders persisted options under assistant messages and either sends a question or prefills the composer.

**Tech Stack:** FastAPI, Pydantic, httpx, pytest, Vue 3, TypeScript, Vitest, Playwright.

## Global Constraints

- AI output remains advisory and cannot directly change case state.
- Every AI option must be persisted in message metadata so it survives history reload.
- Qwen failures must fall back to local simulation and local follow-up suggestions.
- User-visible text must not contain internal follow-up delimiters.
- Follow-up labels must stay short; detailed text belongs in the message sent or prefilled.

---

### Task 1: Structured Follow-up Options

**Files:**
- Modify: `backend/app/services/ai.py`
- Modify: `backend/app/schemas/case.py`
- Modify: `backend/app/routes/cases.py`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/views/WorkspaceView.vue`
- Modify: `frontend/src/styles/base.css`
- Modify: `docs/api/接口契约_v1.md`
- Test: `backend/tests/test_demo_flow.py`
- Test: `frontend/src/utils/followUps.test.ts`
- Test: `frontend/e2e/demo-flow.spec.ts`

**Interfaces:**
- Produces: `FollowUpOption { id: str, label: str, message: str, kind: "send" | "fill" }`.
- Produces: `StructuredAIResult.follow_up_options`.
- Produces: assistant message metadata at `metadata_json.structured.follow_up_options`.

- [x] Add failing backend tests for local follow-up generation and user-visible Qwen delimiter removal.
- [x] Add failing frontend tests for parsing persisted options.
- [x] Add a failing Playwright test that clicks a follow-up question and receives a new assistant reply.
- [x] Implement backend generation, validation, prompt parsing, and persistence.
- [x] Render clickable follow-up chips and support send/prefill behavior.
- [x] Update the contract and test the complete AI consultation path.

### Task 2: Qwen-backed Simulation with Fallback

**Files:**
- Modify: `backend/app/services/simulation.py`
- Modify: `backend/app/routes/simulations.py`
- Modify: `docs/api/接口契约_v1.md`
- Test: `backend/tests/test_simulations.py`

**Interfaces:**
- Produces: `async generate_simulation_reply(role_type, scenario, content, turn_count) -> str`.
- Consumes: `QIANWEN_API_KEY` and `QIANWEN_MODEL` from existing settings.

- [x] Add a failing test that injects a fake Qwen transport and verifies the model response is used.
- [x] Add a fallback test that verifies template output remains available when Qwen fails.
- [x] Implement async Qwen simulation prompts and exception fallback.
- [x] Run backend, frontend, and affected E2E suites.
