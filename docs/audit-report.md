# PRAXIS-SENATE — Dashboard & Architecture Audit Report

**Date**: 2026-04-11  
**Auditor**: Code Audit  
**Scope**: Full repo architecture, UI/dashboard, kanban board, usability, design, and usefulness

---

## 1. Executive Summary

PRAXIS-SENATE is a **multi-agent orchestration system** with a Manager-Worker-Critic architecture, LLM integration, Docker-based command execution, and both CLI and web dashboards. The project shows strong architectural foundations and an impressive feature set for its stage, but suffers from **significant duplication, CSS conflicts, kanban inflexibility, lack of drag-and-drop, no real-time task streaming, missing state persistence in the frontend, and several UX anti-patterns** that limit its usefulness as a production control loop dashboard.

This report identifies **27 specific issues** across 5 categories and proposes **23 concrete improvements** with prioritization.

---

## 2. Architecture Analysis

### 2.1 Two Parallel Codebases (CRITICAL)

The repo contains two independent implementations:

| Aspect | `code/` (v1) | `multi_agent_system/` (v2) |
|--------|--------------|---------------------------|
| Scope | 5 files, ~2500 LOC | ~6000+ LOC, 13+ modules |
| EventBus | `MessageBus` (pub/sub with topics) | `EventBus` (async queue, 16 event types) |
| State | In-memory `StateManager` | `StateManager` + SQLite + `PersistentStateManager` + `TaskDatabase` |
| Agents | Manager + 3 Workers | SeniorAgent + CriticAgent + N Workers + LLM |
| Dashboards | None (CLI only in `main.py`) | CLI (`cli_dashboard.py`) + Interactive + Web |

**Problem**: The `code/` directory is dead weight. It uses a different message model (`MessageBus` with topics vs `EventBus` with event types) and different agent classes (`ManagerAgent` vs `SeniorAgent`). There's no bridge between the two.

**Recommendation**: Remove `code/` or clearly mark it as archived/deprecated. The canonical implementation is `multi_agent_system/`.

### 2.2 State Management Overlap

There are **three** state management systems:

1. `StateManager` — in-memory dict with EventBus integration
2. `PersistentStateManager` — extends StateManager with SQLAlchemy dual-write
3. `TaskDatabase` — JSON-file-based persistence with subscriptions

**Problem**: It's unclear which is the source of truth. `TaskDatabase` and `StateManager` both persist tasks but through different mechanisms. `StateManager` uses SQLite while `TaskDatabase` uses JSON files. The API routes likely use one or the other inconsistently.

**Recommendation**: Consolidate into a single persistence layer. `TaskDatabase` with real-time subscriptions is the better API — promote it as the canonical state manager and deprecate the dual-write pattern in `PersistentStateManager`.

### 2.3 EventBus Architecture

The `EventBus` in `core/event_bus.py` has 16 event types including `CRITIQUE_RECEIVED`, `TASK_DECOMPOSED`, `LLM_PROMPT`, `LLM_RESPONSE`, `AGENT_THINKING`, `TASK_HALTED`, `TASK_FEEDBACK`, `TASK_RESUMED`. This is well-designed.

**Problem**: All event types are in a single `EventType` enum. As the system grows, this will become unwieldy. There's no namespacing (e.g., `TASK.CREATED`, `TASK.COMPLETED`).

**Recommendation**: Consider hierarchical event naming (`task.created`, `task.completed`, `llm.prompt`, `agent.thinking`) or at least group them into sub-enums.

### 2.4 LLM Integration

The `LLMManager` supports OpenAI, Anthropic, Google, OpenRouter, and MiniMax with priority-based fallback and exponential backoff. This is solid.

**Problems**:
- No token usage tracking exposed to the dashboard
- No cost estimation visible to the user
- The dashboard shows `llm_provider` in the header but not usage stats
- LLM responses are truncated to 300/500/800 chars in the web dashboard (`getLlmEntryContent()`)

**Recommendation**: Add a token/cost meter to the header and expose per-task LLM usage in the task inspector.

### 2.5 Security

The `security/__init__.py` module provides `CommandSafetyValidator`, `RateLimiter`, `InputSanitizer`, and `SecurityAuditor`. Docker containers have network disabled, read-only filesystem, resource limits.

**Problem**: The security audit log goes to a file (`data/security_audit.log`) but is never exposed in the dashboard. The rate limiter configuration is hardcoded, not exposed.

**Recommendation**: Add a security panel to the web dashboard showing recent audit events, blocked commands, and rate limit status.

---

## 3. Dashboard Deep Dive

### 3.1 Three Dashboard Implementations

There are three dashboards, each with different capabilities:

| Feature | CLI Dashboard | Interactive Dashboard | Web Dashboard |
|---------|--------------|----------------------|--------------|
| Real-time updates | Live (Rich Live) | Manual menu | WebSocket/SSE |
| Add task | No | Yes | Yes |
| View tasks | Table | Table | Kanban board |
| Manage agents | No | CRUD | Pause/Resume |
| Manage roles | No | CRUD | View/Edit |
| Send corrections | No | Yes | Feedback form |
| LLM stream | No | No | Yes |
| Task inspector | No | No | Yes (modal) |
| Human-in-the-loop | No | Yes | Yes |

**Problem**: The CLI and Interactive dashboards are effectively dead code. The CLI dashboard (`cli_dashboard.py`) can't create tasks or interact with agents — it's read-only. The Interactive dashboard (`interactive_dashboard.py`) has a stubbed-out `_command_loop` (line 126-137) that literally `continue`s in a loop without reading input, and `_display_status()` is a no-op (`pass`). This means the Interactive dashboard's command loop **doesn't work** — users can only interact through `show_menu()` which is called once, not continuously.

**Recommendation**: Remove both CLI dashboards or merge their unique functionality (like CRUD agent/role management) into the web dashboard. The web dashboard should be the single source of truth.

### 3.2 Web Dashboard — Kanban Board Analysis

The kanban board is the central UI element. It has 5 columns: Pending, In Progress, Completed, Failed, Halted.

#### Critical Issues

**ISSUE K-1: No Drag-and-Drop**

Tasks can only move between columns via the backend (agent assignment, status changes). Users cannot drag tasks to reprioritize, reassign, or change status. The kanban is effectively a **read-only status display**, not an interactive board.

This fundamentally undermines the "control the loop" purpose. If a user sees a task stuck in `in_progress`, they should be able to drag it to `halted` or back to `pending`. Currently they must:
1. Click the task card
2. Open the Task Inspector modal
3. Find the "Human Intervention" section
4. Type feedback
5. Click "Halt"

That's 5 clicks/actions for what should be a single drag.

**Fix**: Implement HTML5 drag-and-drop on `.kanban-column` elements. On drop, call `PATCH /api/tasks/{id}` with the new status. This is the single most impactful improvement.

**ISSUE K-2: No Task Priority Visualization**

Tasks are displayed in insertion order within each column. There's no visible priority, no sorting options, no ability to reorder. The task cards show `task.type` in the meta row, but not priority.

**Fix**: Add a priority indicator (colored dot or number) on each task card. Allow sorting by priority, creation time, or assignment.

**ISSUE K-3: No Task Count Summary / Header Stats**

The dashboard has no overall statistics visible at a glance. The old v1 CSS had a `.task-board` with counters, but the current design puts the count badge on each column header. There's no global overview like "12 tasks total, 3 in progress, 2 failed, 89% success rate."

**Fix**: Add a compact stats bar above the kanban board or in the header: total tasks, active, completed rate, avg duration.

**ISSUE K-4: Kanban Columns Are Horizontally Scrolling, Not Wrapping**

At `max-width: 1600px` with 5 columns, the kanban works fine on wide monitors. But on smaller screens (<1200px), columns become horizontally scrollable with `overflow-x: auto`. This makes the "Completed" and "Failed" columns invisible without scrolling.

**Fix**: Consider a responsive layout that stacks columns on narrow viewports, or use a tab-based view for mobile. Also consider a swimlane view grouping tasks by agent.

**ISSUE K-5: No Task Creation from Board**

The "+ New Task" button is in the header, disconnected from the kanban board. In most kanban tools, users can click a "+" button at the top of each column to create a task directly in that status.

**Fix**: Add a "±" button at the bottom of the Pending column (or each column) that opens the task creation modal with the column's status pre-selected.

**ISSUE K-6: No Task Dependencies or Relationships**

Tasks have no visual relationship to each other. There are no dependency arrows, no parent-child linking, no indication that "Task A must complete before Task B starts." The `task.subtasks` are shown in the inspector modal, but never on the board.

**Fix**: Add visual connectors between related tasks (using SVG lines or a library like react-flow when migrating to a framework). At minimum, show a "has N subtasks" indicator on task cards.

**ISSUE K-7: No Time Tracking / Duration Display**

Task cards show duration as `task.started_at → task.completed_at`, but if a task is in-progress, it just shows "In progress..." with no elapsed time counter. There's no timer showing how long a task has been running.

**Fix**: Add a live elapsed time counter on in-progress task cards. Use `setInterval` to update every second.

---

## 4. UI Design Issues

### 4.1 Duplicate CSS (CRITICAL)

The `main.css` file contains **two complete, conflicting CSS implementations** stacked on top of each other:

- **Lines 1-1873**: "Overhaul v2.0" — Deep space command center aesthetic with glass morphism, design tokens, Space Grotesk/DM Sans/JetBrains Mono fonts, CSS custom properties, animations, modern styling.

- **Lines 2163-4271**: A completely different, older style using `--accent-primary: #e94560`, `--accent-secondary: #6c3fb5`, Inter font, different border-radius, different shadow system, different color scheme.

This creates multiple problems:
- The v2 selectors **override** v1, but since v1 loads second in the cascade (it's below), **v1's duplicate rules actually override v2's** for any shared selector names.
- Elements like `.task-card`, `.kanban-column`, `.agent-card`, `.event-item`, `.modal`, `.toast`, etc. get both sets of styles applied, creating visual inconsistencies.
- The v1 style uses different color variables (`--accent-primary: #e94560` red vs v2's `--accent: #818cf8` purple), so some elements appear red while others appear purple.
- The v1 sidebar uses `left: -320px` for hiding while v2 uses `transform: translateX(-100%)`, causing **both transforms to compete**.

**Fix**: Delete the entire second CSS block (lines 2163-4271). Keep only the v2 "Overhaul" styles. Audit for any selectors only defined in v1 that would be lost.

### 4.2 Color System Inconsistency

Even within the v2 CSS, there are inconsistencies:
- The kanban `data-status="halted"` column gets `border-left: 2px dashed` while other statuses use `border-left: 3px solid`. This is intentional but the dash pattern makes halted tasks look broken rather than paused.
- `.task-card.halted::before` adds a "⏸" emoji positioned absolutely, but this overlaps with the task description text.

### 4.3 Accessibility Issues

- **No keyboard navigation** for kanban cards (only click opens inspector)
- **No ARIA labels** on interactive elements
- **No focus indicators** on task cards or kanban columns
- **Color-only encoding**: Task status is communicated solely through color (green/red/yellow/blue). No icon or text pattern for colorblind users.
- **No `prefers-reduced-motion`** media query — animations play regardless of user preference
- **No screen reader support**: The kanban board structure is not announced; screen readers would see a flat list of divs with no semantic meaning.

**Fix**: Add ARIA roles (`role="list"` on columns, `role="listitem"` on cards, `aria-label` on status indicators), tabindex on cards, `prefers-reduced-motion` media query, and status icons alongside colors.

### 4.4 Empty State Handling

Empty columns show nothing. There's no visual cue that "this is where tasks will appear" or "no pending tasks — great job!" The CSS defines `.empty-state` but the JS often removes it and never adds meaningful empty states per column.

**Fix**: Add per-column empty states with action buttons ("Create your first task" in the Pending column).

### 4.5 Responsive Design Gaps

- At 1200px, the layout switches to single column but the kanban still scrolls horizontally, creating a poor mobile experience.
- The sidebar overlay doesn't dismiss when tapping outside on mobile (the click handler only checks clicks on `.main-content`, not on the overlay backdrop).
- The Task Inspector modal has a fixed `max-width: 900px` which is fine on desktop but barely usable at 320px mobile width.

### 4.6 Animation Overload

The v2 CSS has 8+ animations: `panelReveal`, `cardSlideIn`, `cardPulse`, `statusPulse`, `dotRing`, `llmFadeIn`, `eventFadeIn`, `toastIn`, `toastOut`, `modalOverlayIn`, `modalContentIn`, `phasePulse`, `typingBounce`, `shimmer`, `agentBusy`. While individually tasteful, combined they create visual noise, especially when many events fire simultaneously.

**Fix**: Consider reducing to 3-4 essential animations (card entrance, toast, modal). Add a "Reduce animations" toggle in settings.

---

## 5. Functional Gaps & Usefulness Issues

### 5.1 No Task Board Interactivity

As detailed in K-1, the kanban board is read-only. For a system designed to "control the loop," this is the primary usability gap.

### 5.2 No Search or Filtering

The task filter dropdown (`#taskFilter`) only filters by status. There's no:
- Text search for task descriptions
- Filter by agent assignment
- Filter by date range
- Filter by task type
- Search within the activity log

**Fix**: Add a search bar above the kanban board with real-time filtering. Add filter chips for agent, type, and date.

### 5.3 No Batch Operations

Users cannot:
- Select multiple tasks and bulk-halt, bulk-resume, or bulk-reassign
- Clear all completed tasks
- Re-run failed tasks

### 5.4 No "Re-run" or "Retry" for Failed Tasks

The inspector modal has "Halt" and "Send & Resume" but no "Retry" button for failed tasks. A failed task is a dead end in the UI.

**Fix**: Add a "Retry Task" action that creates a new task with the same description, or sends a `POST /api/tasks/{id}/retry` endpoint.

### 5.5 No Agent-Task Relationship View

The agent pool shows static information (agent ID, status, tasks completed). There's no visual link between which agent is working on which task. When a user clicks an agent, they should see that agent's current and recent tasks.

**Fix**: Clicking an agent card should filter the kanban board to show only that agent's tasks. Better yet, show a mini-activity feed inside the agent card.

### 5.6 LLM Stream Is Not Actually Streaming

The "Live LLM Stream" section shows individual events, not a real token-by-token stream. The `handleLlmEvent()` function creates new DOM elements for each event, not appending tokens to an existing stream. This means:
- Users see discrete chunks, not a typing effect
- The "typing indicator" is a simple bouncing dot, not actual streaming text
- Long responses get truncated to 300-800 characters

**Fix**: Implement Server-Sent Events token streaming with incremental DOM updates. Or use the existing typing indicator pattern but populate it word-by-word from the response.

### 5.7 No Task Timeline or Gantt View

For a system that orchestrates multi-step tasks with dependencies, there's no temporal visualization. Users can't see:
- How long each task took
- What happened in parallel vs sequentially
- Where bottlenecks occurred

**Fix**: Add a simple timeline view (horizontal bar chart) showing task duration and overlap. A Gantt chart would be ideal but even a simple timeline would help.

### 5.8 No Export or Reporting

There's no way to:
- Export task results as JSON/CSV/Markdown
- Generate a summary report of a session
- Copy task output to clipboard from the inspector

The `generate_task_report()` method exists in `SeniorAgent` but its output is never surfaced in the dashboard.

### 5.9 No Notification Sound or Desktop Notification

When tasks complete or fail, only a toast appears. For a system meant to run in the background while users do other work, audio or desktop notifications via the Notification API would be essential.

**Fix**: Add `Notification.requestPermission()` on connect, then trigger desktop notifications on `task_completed`, `task_failed`, and `task_halted` events.

### 5.10 Critic Panel Is Passive

The Critic Agent panel shows critiques after they happen. Users cannot:
- Request a critique on demand (trigger `POST /api/tasks/{id}/critique` exists but has no UI button)
- See the critique before it's applied (the TODOs say "show task progress updates" is incomplete)
- Configure critique behavior (blocking vs non-blocking, confidence threshold)

**Fix**: Add a "Request Critique" button on each in-progress task. Show a "Critique pending..." state in the task card.

---

## 6. Specific Code Quality Issues

### 6.1 CSS Duplication

As noted in section 4.1, **2,108 lines of duplicate CSS** (lines 2163-4271) need to be removed. This is the most critical frontend issue.

### 6.2 JavaScript Anti-Patterns

- **Global state mutation**: `tasks`, `agents`, `events`, `critiques` are all module-level `let` arrays mutated directly throughout the code. No state management pattern.
- **No error boundaries**: `showTaskInspector()` silently fails if the task isn't in the local array and the API call fails. Network errors show generic toasts.
- **DOM manipulation**: All rendering is done via innerHTML with template literals. This is XSS-prone. The `escapeHtml()` function exists but `task.description` and `task.assigned_to` are interpolated into templates without escaping.
- **Event listener leaks**: `setupEventListeners()` and `setupKeyboardShortcuts()` add document-level listeners that are never removed.
- **Polling + WebSocket redundancy**: `setupTaskPolling()` runs every 5 seconds regardless of WebSocket status, doubling requests when the connection is healthy.

### 6.3 XSS Vulnerability

Multiple places inject raw data into HTML:

```javascript
// app.js line 690-703
card.innerHTML = `
    <div class="task-desc">${desc.substring(0, 60)}${desc.length > 60 ? '...' : ''}</div>
`;
```

`desc` comes from `task.description` which could contain `<script>` tags or event handlers. Only `event.data` entries use `escapeHtml()`, but task descriptions and agent IDs are injected raw.

**Fix**: Sanitize all user-controlled data before innerHTML insertion, or switch to `textContent`/`createElement` patterns.

### 6.4 Hardcoded API Base URL

```javascript
const API_BASE = window.location.origin;
```

This breaks if the dashboard is served from a different origin than the API. No proxy configuration for development.

### 6.5 No Error Boundary for WebSocket

When WebSocket fails, the dashboard falls back to polling, but this is transparent to the user. No visual indication that real-time updates are degraded.

---

## 7. Improvement Roadmap

### Priority 1 — Critical (Do Immediately)

| # | Improvement | Impact | Effort |
|---|------------|--------|--------|
| 1 | **Remove duplicate CSS** (lines 2163-4271) | Fixes visual bugs, reduces file by 50% | Low |
| 2 | **Add drag-and-drop to kanban** | Transforms read-only board to interactive | Medium |
| 3 | **Fix InteractiveDashboard command loop** | Makes CLI dashboard functional | Low |
| 4 | **Remove or archive `code/` directory** | Eliminates confusion | Low |
| 5 | **Fix XSS in task cards** | Security critical | Low |

### Priority 2 — High Impact

| # | Improvement | Impact | Effort |
|---|------------|--------|--------|
| 6 | **Add task search bar** with real-time filtering | Major usability gain | Medium |
| 7 | **Add elapsed time counters** on in-progress cards | Situational awareness | Low |
| 8 | **Surface LLM token/cost stats** in header | Value visibility | Medium |
| 9 | **Add "Retry" action** for failed tasks | Workflow continuity | Low |
| 10 | **Consolidate StateManager** into TaskDatabase | Architecture cleanup | Medium |
| 11 | **Desktop notifications** for task events | Background monitoring | Low |

### Priority 3 — Polish & Delight

| # | Improvement | Impact | Effort |
|------|------------|--------|--------|
| 12 | **Task dependency arrows** on kanban | Visual relationships | High |
| 13 | **Agent-task linking** (click agent → filter tasks) | Cross-referencing | Low |
| 14 | **Timeline/Gantt view** | Temporal understanding | High |
| 15 | **Export task report** (JSON/Markdown) | Reporting | Low |
| 16 | **"Request Critique" button** on tasks | Proactive review | Low |
| 17 | **Per-column empty states** with action buttons | UX polish | Low |
| 18 | **Accessibility pass** (ARIA, focus, reduced motion) | Compliance | Medium |
| 19 | **Add search to activity log** | Information retrieval | Low |
| 20 | **Batch operations** (select multiple → halt/resume) | Efficiency | Medium |
| 21 | **Real LLM token streaming** vs chunk display | UX fidelity | High |
| 22 | **Security events panel** in dashboard | Audit visibility | Medium |
| 23 | **Mobile-responsive kanban** (stacked columns) | Mobile usability | Medium |

---

## 8. Kanban Board Visual Improvements — Detailed

### 8.1 Current Visual Design Analysis

The v2 kanban uses glass morphism panels on a dark background with purple accent (`#818cf8`). Cards have left-border color coding per status. The design is sophisticated but has functional gaps:

**What works well:**
- Color coding is consistent and attractive
- Card animations (`cardSlideIn`, `cardPulse`) provide satisfying feedback
- Column headers with count badges give quick status overview
- Toast notifications are well-designed
- The phase indicator on agent cards (`decomposing`, `processing`, etc.) is informative
- LLM log entries with syntax highlighting are a standout feature

**What's missing or broken:**
- Cards look identical within a column — no visual hierarchy
- No priority indicator
- No progress bar or completion percentage
- No task type icons (code task vs research task vs review task)
- No "new task" affordance within columns
- Column widths are equal, but Completed could be wider (more cards typically)
- Halted column uses dashed left-border which looks like a rendering error

### 8.2 Proposed Kanban Redesign

**A. Visual Differentiation**

| Current | Proposed |
|---------|----------|
| All cards look same size | Add size based on priority (compact/normal/expanded) |
| Left-border color only | Left-border + subtle background tint per status |
| No icons | Add type icons: 🔧 Code, 🔍 Research, 📝 Review, 🏗️ Architecture |
| No progress | Add micro progress bar for in-progress tasks |

**B. Interactive Enhancements**

| Current | Proposed |
|---------|----------|
| Click → modal inspector | Click → slide-in panel (no modal, keeps board visible) |
| No drag-and-drop | React Beautiful DnD or sortable.js |
| No column + button | Add "+" at top of Pending column |
| No quick actions | Add hover actions: ▶ Start, ⏸ Halt, ⋮ More |
| No batch select | Add checkbox in card header for multi-select |

**C. Layout Optimizations**

| Current | Proposed |
|---------|----------|
| 5 equal columns | Pending (1.2fr), In Progress (1.5fr), Completed (1.2fr), Failed (0.8fr), Halted (0.8fr) |
| Fixed max-height 400px | Dynamic height based on viewport, with column scroll |
| No column totals | Add "N tasks, avg Xm Xs" summary per column |
| No swimlanes | Add toggle for "Group by Agent" swimlane view |

**D. Dynamic Elements**

| Element | Current | Proposed |
|---------|---------|----------|
| Task transition | Card appears in new column | Animate card sliding between columns |
| New task | Card appears instantly | Slide-in from top with stagger delay |
| In-progress | Static "In progress..." text | Pulsing glow + elapsed timer |
| LLM activity | Separate panel below | Mini streaming indicator on the task card itself |
| Agent assignment | Text badge | Agent avatar with color coding matching agent card |

---

## 9. Architecture Recommendations (Long-Term)

### 9.1 Migrate to a Frontend Framework

The current dashboard is vanilla HTML + CSS + JS (~3,800 lines of CSS + ~1,500 lines of JS). As features grow, this becomes unmaintainable. Consider:

- **React/Next.js** with component architecture
- **Vue.js** for simpler integration with the existing API
- **Svelte** for minimal bundle size

The kanban board especially would benefit from a reactive framework + drag library.

### 9.2 State Management for Frontend

Currently, the frontend has no state management. `tasks`, `agents`, `events` are global arrays mutated in place. Consider:

- **Zustand** (simplest, good with React)
- **Svelte stores** (if Svelte)
- **Custom store** with event sourcing from the WebSocket

### 9.3 Graph Visualization for Task Dependencies

For task relationships, consider:
- **D3.js** for custom force-directed graphs
- **React Flow** for interactive node-based diagrams
- **Cytoscape.js** for large graphs

This would replace the flat kanban view with an optional "dependency graph" view.

### 9.4 Unify Dashboard Implementations

Delete `cli_dashboard.py` and `interactive_dashboard.py`. Port any unique functionality (role CRUD) to the web dashboard. The web dashboard should be the only interactive interface.

### 9.5 Progressive Enhancement

The web dashboard should work in degraded mode:
- No WebSocket → fall back to polling (already exists but is hidden)
- No JavaScript → basic HTML form for task submission (server-rendered)
- Slow connection → skeleton loaders with optimistic UI updates

---

## 10. Metric Dashboard Proposal

Currently, the header only shows `LLM Provider: minimax` and `Critic Agent: on/off`. Add a compact metrics bar:

```
┌────────────────────────────────────────────────────────────────────────┐
│ PRAXIS-SENATE  ● Connected  │  Tasks: 12 (3⚡ 7✅ 1❌ 1⏸)  │  ⏱ 2m 14s │
│                minimax     │  Tokens: 8.2k  │  Cost: $0.04  │  Critic: ON  │
└────────────────────────────────────────────────────────────────────────┘
```

This gives instant situational awareness without scrolling.

---

## 11. Summary Scores

| Category | Score (1-10) | Notes |
|----------|-------------|-------|
| Architecture | **7** | Solid event-driven design, Docker isolation, LLM fallback. Deducted for dual codebases and triple state management. |
| Code Quality | **5** | Duplicate CSS, XSS vulnerabilities, global mutable state, stubbed CLI commands. Core logic is well-structured though. |
| Visual Design | **7** | v2 glass morphism is attractive and modern. Deducted for duplicate CSS conflicts and animation overload. |
| Kanban UX | **4** | Read-only board in a "control the loop" dashboard is a fundamental limitation. No drag, no search, no priorities. |
| Accessibility | **3** | No ARIA, no keyboard nav on cards, no reduced-motion, color-only status encoding. |
| Usefulness | **6** | Good observability (events, LLM stream, critiques). Limited controllability (can't drag, retry, or batch). |
| Security | **7** | Docker isolation, command whitelist, rate limiter, input sanitization. Deducted for XSS in dashboard and unexposed audit logs. |
| Performance | **7** | WebSocket + SSE, async Python, polling fallback. Deducted for duplicate polling+WS and no debouncing on renders. |

**Overall: 5.75/10** — Strong foundation with significant UX gaps that limit the dashboard's primary purpose of controlling the agent loop.

---

## 12. Immediate Action Items

1. **Delete lines 2163-4271 in main.css** (removes 2,108 lines of duplicate, conflicting styles)
2. **Add drag-and-drop** to kanban columns (even basic HTML5 DnD without a library)
3. **Sanitize all `innerHTML`** injections in app.js with `escapeHtml()`
4. **Add "Retry" button** for failed tasks in the inspector
5. **Add global stats bar** in the header (tasks count, token usage, avg duration)
6. **Remove or clearly deprecate** `code/` directory and CLI dashboards
7. **Add per-column empty states** with "Create task" call-to-action
8. **Implement desktop notifications** via the Notification API

---

*End of Audit Report*