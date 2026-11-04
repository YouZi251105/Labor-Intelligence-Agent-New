# Workflow Editor Preview And Collapse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an edit/preview workspace mode, canvas zoom controls and collapsible rule-package panels without changing the rule-package schema.

**Architecture:** Extend `WorkflowBlockDesigner.vue` with local UI state for preview, panel visibility, zoom and fullscreen. Keep the existing SVG connection renderer and add a scaled viewport wrapper. Add version-list collapse state in `RulePackageCenter.vue`.

**Tech Stack:** Vue 3, TypeScript, CSS Grid, SVG, Vitest, Playwright.

## Global Constraints

- Do not add Vue Flow or another graph dependency in this phase.
- Do not change the rule-package API or persisted schema.
- Preview must be read-only but keep connection highlighting.
- Zoom range is 35% to 160%.
- Desktop and 390x844 mobile layouts must remain usable.

---

### Task 1: Canvas Workspace State

**Files:**
- Modify: `frontend/src/components/WorkflowBlockDesigner.vue`
- Modify: `frontend/src/styles/base.css`

**Interfaces:**
- Produces local state: `previewMode`, `paletteCollapsed`, `inspectorCollapsed`, `zoom`, `isFullscreen`.
- Produces controls: `编辑`, `预览`, `放大画布`, `缩小画布`, `适应画布`, `全屏预览`.

- [ ] **Step 1: Add the top toolbar and mode switch.**
- [ ] **Step 2: Add scaled viewport wrapper and zoom state.**
- [ ] **Step 3: Add fullscreen handling and cleanup listeners.**
- [ ] **Step 4: Make preview read-only and auto-fit.**

### Task 2: Collapsible Panels And Version List

**Files:**
- Modify: `frontend/src/components/WorkflowBlockDesigner.vue`
- Modify: `frontend/src/components/RulePackageCenter.vue`
- Modify: `frontend/src/styles/base.css`

**Interfaces:**
- Produces accessible labels: `折叠积木面板`, `折叠属性面板`, `折叠版本列表`.

- [ ] **Step 1: Collapse the palette into an icon rail.**
- [ ] **Step 2: Allow the inspector to be hidden independently.**
- [ ] **Step 3: Collapse the rule-package version list while preserving selection.**
- [ ] **Step 4: Adjust desktop and mobile grid layouts for each combination.**

### Task 3: Interaction And Responsive Verification

**Files:**
- Modify: `frontend/e2e/demo-flow.spec.ts`

**Interfaces:**
- Consumes controls from Tasks 1 and 2.

- [ ] **Step 1: Test preview hides editor panels and switches back.**
- [ ] **Step 2: Test zoom percentage and fit-to-canvas.**
- [ ] **Step 3: Test palette, inspector and version-list collapse.**
- [ ] **Step 4: Run desktop and mobile Playwright projects.**

### Task 4: Documentation And Screenshots

**Files:**
- Modify: `README.md`
- Modify: `docs/admin/管理员使用手册.md`
- Modify: `docs/admin/规则包Excel填写说明.md`
- Modify: `docs/product/当前功能与边界.md`
- Modify: `docs/development/两人并行开发约定.md`
- Modify: `docs/demo/演示脚本.md`
- Update: `docs/screenshots/admin-rule-packages-desktop.png`
- Update: `docs/screenshots/admin-rule-packages-mobile.png`

- [ ] **Step 1: Document edit/preview, zoom, fullscreen and collapse controls.**
- [ ] **Step 2: Update screenshots from the verified UI.**
- [ ] **Step 3: Run frontend unit tests, typecheck, build and backend regression.**
