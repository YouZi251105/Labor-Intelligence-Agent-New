# Workflow Connection Canvas And Mobile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw configured workflow paths as interactive SVG connections and make the rule-package designer practical on mobile devices.

**Architecture:** Keep the existing rule-package schema unchanged. Measure blocks and outlet ports in the browser, derive edge geometry in a pure utility, render an SVG layer below the existing absolutely positioned blocks, and add touch-friendly position controls to the inspector.

**Tech Stack:** Vue 3, TypeScript, SVG, Vitest, Playwright.

## Global Constraints

- Do not add a graph library or any new npm dependency.
- Connections are presentation-only and must not modify the rule-package schema.
- Unconnected outlets never render a line.
- Mobile must support click-to-add, controlled target selection, touch scrolling and directional position controls.
- Existing Excel, validation, review, publish and runtime behavior must remain compatible.

---

### Task 1: Edge Geometry Utility

**Files:**
- Create: `frontend/src/utils/workflowEdges.ts`
- Create: `frontend/src/utils/workflowEdges.test.ts`

**Interfaces:**
- Produces: `collectWorkflowConnections(content)` returning source node, option and target node records.
- Produces: `buildWorkflowEdge(input)` returning `{ path, labelX, labelY }`.

- [ ] **Step 1: Write failing tests for connection collection and both layout directions.**
- [ ] **Step 2: Run `npm test -- --run workflowEdges` and confirm failure.**
- [ ] **Step 3: Implement the pure geometry utility with cubic Bezier paths and midpoint labels.**
- [ ] **Step 4: Re-run the focused test and confirm pass.**

### Task 2: SVG Connection Layer

**Files:**
- Modify: `frontend/src/components/WorkflowBlockDesigner.vue`
- Modify: `frontend/src/styles/base.css`

**Interfaces:**
- Consumes: `collectWorkflowConnections` and `buildWorkflowEdge` from Task 1.
- Produces: `.workflow-connections`, `.workflow-connection` and `.workflow-connection__label` UI hooks for E2E.

- [ ] **Step 1: Add the scrollable stage, SVG marker and edge rendering template.**
- [ ] **Step 2: Measure canvas, blocks and outlet ports with `ResizeObserver` and requestAnimationFrame.**
- [ ] **Step 3: Recalculate after target changes, node movement, node deletion and type changes.**
- [ ] **Step 4: Add selected-edge highlighting and click-to-select behavior.**
- [ ] **Step 5: Run unit tests, typecheck and production build.**

### Task 3: Mobile Canvas Controls

**Files:**
- Modify: `frontend/src/components/WorkflowBlockDesigner.vue`
- Modify: `frontend/src/styles/base.css`

**Interfaces:**
- Produces: accessible labels `上移积木`, `下移积木`, `左移积木`, `右移积木` and `自动整理`.

- [ ] **Step 1: Add direction buttons to the editable inspector and clamp positions inside the stage.**
- [ ] **Step 2: Add deterministic layered auto-layout from the start node.**
- [ ] **Step 3: Update responsive CSS for toolbar wrapping, compact palette, touch-sized controls and single-direction scrolling.**
- [ ] **Step 4: Verify 390x844, 1366x768 and 1440x1000 layouts in Playwright.**

### Task 4: Regression Tests And Documentation

**Files:**
- Modify: `frontend/e2e/demo-flow.spec.ts`
- Modify: `docs/admin/管理员使用手册.md`
- Modify: `docs/admin/规则包Excel填写说明.md`
- Modify: `docs/product/当前功能与边界.md`
- Modify: `docs/development/两人并行开发约定.md`
- Modify: `docs/demo/演示脚本.md`

**Interfaces:**
- Consumes: SVG and mobile controls from Tasks 2 and 3.

- [ ] **Step 1: Extend the rule-package E2E to assert connection count, target changes and mobile controls.**
- [ ] **Step 2: Document connection labels, selection, unconnected outlets, auto layout and mobile operating steps.**
- [ ] **Step 3: Run frontend unit tests, typecheck, production build, backend tests and full Playwright desktop/mobile projects.**

### Task 5: Integration And Deployment

**Files:**
- No source files.

- [ ] **Step 1: Fetch latest remote `main` when network access is available and merge it into the feature branch.**
- [ ] **Step 2: Resolve conflicts without reverting unrelated work, rerun all tests and merge to `main`.**
- [ ] **Step 3: Push `main`, update the isolated validation deployment, verify health and report the public validation URL.**
