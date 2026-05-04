---
title: agent-dashboard — design vision
version: 4
updated: 2026-04-26
status: active
---

# agent-dashboard — design vision

## Who this document is for

This document is for Python developers building agent-powered applications who
want to understand what `agent-dashboard` is, what it does, and whether it fits
their use case.

---

## The problem

LLM agents operating over structured workspaces — inboxes, task queues,
communication threads, dashboards — need to receive two things at each step:

1. **What is here.** The current state of the workspace: pending items,
   notable events, available actions.
2. **What to do.** The operating goal for this moment: what to prioritise,
   which actions to take, what to avoid, when to stop.

These two things are different in nature, and keeping them distinct is the
central design intent of `agent-dashboard`. "What is here" is data — it
changes every session, every turn. "What to do" is policy — it is stable for
a given screen family and changes only when the domain logic changes. The
library names this distinction through its type structure and rendering order;
it does not enforce it mechanically. A consuming application can put policy
into highlights or data into `screen_instructions`. What the library provides
is a vocabulary and a convention that makes the intended separation legible and
reproducible.

The naive approach merges them: dump everything into a free-form system prompt
and let the agent sort it out. This breaks down quickly:

- **Inconsistency.** Each screen is formatted differently. The agent cannot
  build reliable pattern-matching across sessions.
- **Verbosity.** Unstructured dumps expand without bound. Token budget is
  wasted on scaffolding instead of content.
- **No agent-UX contract.** The agent has no reliable way to know which
  actions require approval or what the screen expects it to do next. Every
  new screen family requires the agent to re-learn from scratch.
  (`action_id` semantics — what a given identifier means to the agent — are
  a consumer responsibility; the library renders `action_id` verbatim and
  does not contract its meaning.)
- **Multi-consumer divergence.** When two applications independently invent
  screen formats, they drift apart. There is no shared vocabulary, no shared
  test patterns, and no way to transfer institutional knowledge between
  teams. The format is entangled with each codebase that produces it.
- **Untestable and irreproducible prompt assembly.** Free-form prompt
  construction is hard to unit-test and does not produce identical output
  for identical input — small changes in assembly order or string
  interpolation silently change what the agent receives. This makes
  debugging and regression-testing prompt changes expensive.

---

## What agent-dashboard provides

A **screen** is an immutable snapshot of what an agent sees in a structured
workspace at a given moment, rendered as plain text for inclusion in an LLM
prompt.

`agent-dashboard` is a small Python library with two responsibilities:

**1. A canonical data model for agent workspace screens.**

Three immutable dataclasses — `DashboardHighlight`, `DashboardActionRef`,
`DashboardScreen` — form a shared vocabulary for describing what an agent sees.
Any application that needs to show an agent a structured workspace view can
use these types. The model is transport-agnostic, runtime-agnostic, and has
no opinion on how screens are assembled or how actions are executed. The data
types make no transport assumptions; converting a screen to a dict or JSON
for transmission over WebSocket, SSE, or other transports is the consuming
application's responsibility (serialization helpers are available in
`agent_dashboard.serialization`).

**2. A deterministic plain-text renderer.**

`render_screen(screen, *, token_budget)` converts a `DashboardScreen` to a
token-bounded plain-text string ready for inclusion in an LLM prompt. The
renderer is a pure function: same input, same output, always. It handles
truncation, section ordering, and action formatting consistently across all
screen families.

That is all the library does. It does not execute actions, manage state,
route messages, or call any model API. The consuming application owns all of
that.

---

## Relationship to other documents

| Document | What it answers |
|----------|----------------|
| `VISION.md` (this file) | What is the library for, and what does it feel like to use? |
| `proposals/boundary.md` | What enters the library and what stays in the consumer? How was each coupling decision made? |
| `proposals/external-dev-api.md` | What does the library promise, field by field? What are the exact rendering semantics? |
| `notes/screen-agent-ux.md` | What are the agent-UX risks in the current design, and how are they mitigated? |
| `decisions/` | Accepted, immutable records of decisions that were once proposals. |
| `glossary.md` | Shared vocabulary used across all design documents. |

---

## The developer experience

A developer building a screen for an agent-powered application should be able
to:

1. **Construct a screen** by assembling domain data into the three dataclasses.
   No subclassing, no registration, no framework. Just data.

2. **Render it** with a single function call and pass the result to their LLM.
   `render_screen(screen, token_budget=N)` takes an integer budget in approximate
   tokens. The renderer converts this to a character ceiling via a 4× multiplier
   (`max(32, token_budget * 4)`) and truncates output that exceeds it, appending
   `"... [truncated]"`. The budget is an approximation, not a tokenizer count —
   developers who size their budgets tightly should be aware that actual token
   consumption may vary.

3. **Instruct the agent** about the screen's operating context by filling in
   `screen_instructions` — a short plain-text field that the renderer places
   after the View state block and before highlights and actions. The rendering
   order is: View state (collapsed or expanded — informational; the renderer
   prints it but does not alter output based on it) → `screen_instructions` →
   Highlights → `body_lines` → Actions. The agent reads the header first,
   then task framing, then highlighted items, then body content, then actions.

4. **Signal approval requirements** by setting `requires_approval=True` on
   any action reference that has external side effects. The renderer appends
   `[requires approval]` to that action's line. The agent sees it at the
   point of decision.

5. **Add fields without friction.** Because the library imposes no subclassing,
   registration, or adapter interface, a consuming application is free to carry
   its own fields (routing keys, message refs, etc.) in its own dataclass and
   convert to the library type at rendering time. The library's narrow surface
   leaves that space entirely to the consumer.

The golden path — from zero to a rendered screen — should take around
fifteen to twenty lines of code and no documentation beyond the type
signatures. As a sketch:

```python
from agent_dashboard import DashboardScreen, DashboardHighlight, render_screen

screen = DashboardScreen(
    dashboard_id="inbox",
    screen_id="turn-42",
    breadcrumb=("Inbox",),
    item_count=1,
    body_lines=(),
    screen_instructions="Reply to the oldest unread message first.",
    highlights=(
        DashboardHighlight(
            highlight_id="msg-1",
            title="Unread messages",
            summary="3 unread messages.",
            severity="high",
        ),
    ),
)
rendered = render_screen(screen, token_budget=512)
# Pass `rendered` directly into your LLM prompt.
```

---

## What the library does not do

These are explicit non-responsibilities. They belong in the consuming
application, in a separate layer, or in a companion convention — not in
this library.

- **Action execution.** The library produces text. It does not dispatch
  actions, gate approvals, or call external services.
- **State management.** Screens are value objects. The library has no concept
  of a "current screen", session history, or attention tracking.
- **Dynamic navigation policy.** Per-session, per-turn policy (e.g. "prefer
  replying before signalling task completion when a pending message is
  surfaced") adapts to runtime state that the library cannot see. That logic
  belongs in the session assembly layer of the consuming application.
- **Long-horizon operating instructions.** Detailed, stable operating
  instructions for complex screen families — the kind that govern agent
  behaviour across many sessions and rarely change — belong in your agent
  framework's persistent system-prompt or context-loading mechanism, not in
  `screen_instructions`, which is designed for immediate, per-turn framing.
  The library has no mechanism for loading or managing persistent instructions.
- **Token counting.** `token_budget` is an integer hint in approximate tokens.
  The library applies a 4× character multiplier and truncates. It does not
  call any tokenizer or model API.
- **Field validation.** Open-string fields (`severity`, `status`, `kind`,
  `dashboard_id`, `screen_id`) are rendered as-is. The consuming application
  is responsible for their values.

---

## Design constraints

These constraints are not implementation details — they are load-bearing
properties of the design. Changing any of them would change what the library
is.

**Pure rendering.** `render_screen()` must be a pure function. Any
implementation that introduces side effects, I/O, or global state mutation
violates this constraint.

**Immutable data model.** All three dataclasses are `frozen=True`. Fields
that hold collections are `tuple[...]`. This is not a style choice — it is
what allows screens to be safely passed across threads and cached. Screens
can also be used as dict keys when all field values are hashable; fields
typed as `Any` (such as `metadata`) do not carry this guarantee unless the
consuming application constrains them to hashable types.

**One-way dependency.** The library imports nothing from any consuming
application; the direction is always consumer → library. This means the
library carries no risk of coupling to, or being broken by, any consuming
application's internals.

**Additive-only evolution.** New fields on any public type must have defaults.
Existing call sites that use keyword arguments must not require modification
across minor releases.

**Verbatim pass-through for content fields.** `screen_instructions` is
rendered verbatim. `metadata` is not rendered at all. The library does not
interpret content it does not own.

---

## Document governance

This is the single source of truth for the functional design of `agent-dashboard`.
It describes the problem the library solves, the constraints that shape the
solution, and what "done" looks like from a developer's perspective. It does
not describe implementation decisions — those live in `proposals/` and
`decisions/`. When this document and a proposal conflict, update one of them;
both should be consistent at all times.

Update this document in place. Add an entry to the changelog at the bottom
when the vision materially changes.

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-04-26 | Initial vision. Covers core problem, DX goals, non-responsibilities, and design constraints. |
| 2 | 2026-04-26 | Problem-framing repair (repair round 1). (1) Reframed data/policy distinction as usage convention and design intent, not structural enforcement. (2) Removed `action_id` meaning from agent-UX contract claim; scoped it explicitly as consumer responsibility. (3) Replaced "no portability" bullet with "multi-consumer divergence" as the primary named concrete problem. (4) Changed opening "need to know" to "need to receive" to reflect that the library produces text, not agent knowledge. (5) Added testability and reproducibility as named problems in the problem list. |
| 3 | 2026-04-26 | DX consistency and completeness repair (repair round 2). (1) Added `token_budget` parameter semantics and 4× character-approximation note to DX bullet 2. (2) Corrected DX bullet 3 rendering-order claim: View state precedes `screen_instructions`. (3) Replaced femtobot-specific `SKILL.md` reference in non-responsibilities with framework-agnostic bootstrap language. (4) Qualified dict-key hashability guarantee in Design constraints to acknowledge `metadata` and `Any`-typed fields. (5) Reframed DX bullet 5 from library capability to consumer usage freedom. (6) Replaced `session_complete` femtobot vocabulary in dynamic-navigation-policy example with general language. |
| 4 | 2026-04-26 | Clarity, structure, and readability repair (repair round 3). (1) Moved governance/meta paragraph to a dedicated "Document governance" section near the bottom, so the document opens with orientation. (2) Added explicit audience statement ("Who this document is for") near the top. (3) Added a one-sentence definition of "screen" at the start of "What agent-dashboard provides." (4) Rewrote "Bootstrap skills" non-responsibility bullet to describe the concern in self-contained terms without external jargon. (5) Added a pseudocode sketch to the DX section making the "fifteen lines" claim concrete. (6) Moved "Relationship to other documents" earlier — after "What agent-dashboard provides" and before the DX section. (7) Renamed "No consumer imports" constraint to "One-way dependency" and added a clarifying phrase about import direction. (8) Added inline parenthetical defining "View state" at its appearance in the rendering-order description. |
| 5 | 2026-04-26 | Factual correction and coverage repair (red-team round 1). (1) Fixed golden path sketch: replaced non-existent `DashboardHighlight(label=..., value=...)` with correct field names (`highlight_id`, `title`, `summary`, `severity`). (2) Added missing required `DashboardScreen` fields (`breadcrumb`, `item_count`, `body_lines`) to sketch — previous version raised `TypeError`. (3) Updated "fifteen lines" claim to "fifteen to twenty lines" to match corrected working example. (4) Added `body_lines` to rendering order description in DX bullet 3 — was previously omitted between Highlights and Actions. (5) Added serialization note to transport-agnostic claim clarifying that dict/JSON conversion is consumer responsibility. |
