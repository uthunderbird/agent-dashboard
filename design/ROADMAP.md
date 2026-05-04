---
title: agent-dashboard — working roadmap
version: 2
updated: 2026-05-04
status: active
---

# agent-dashboard — working roadmap

This document tracks what is built, what is designed but not yet implemented,
and what is accepted for future implementation. It is the authoritative
next-step reference for the library.

Design decisions and rationale live in `proposals/`. This document records
outcomes and status only.

---

## Current state

### Implemented

| Module | Public API | Notes |
|--------|-----------|-------|
| `agent_dashboard.protocol` | `DashboardHighlight`, `DashboardActionRef`, `DashboardScreen`, `SeverityLevel`, `StatusValue`, `ViewState` | Frozen dataclasses; Literal type aliases (non-enforcing) |
| `agent_dashboard.renderer` | `render_screen(screen, *, token_budget)` | Pure function, deterministic truncation |
| `agent_dashboard.serialization` | `screen_to_dict(screen)`, `screen_from_dict(data)` | Correct tuple↔list round-trip; ignores unknown fields |
| `agent_dashboard.actions` | `ActionSpec` | Frozen dataclass with `.for_target()` — produces `DashboardActionRef` |
| `agent_dashboard.hub` | `ScreenHub` | Async reactive hub; thread-safe publish; `subscribe()`, `subscribe_from_latest()`; overflow policies; no persistence |
| `agent_dashboard.testing` | `make_screen()`, `screen_diff()`, `ScreenChangeSummary`, `hub_context()` | No pytest coupling; explicit import only (not re-exported from `__init__`) |
| `agent_dashboard.tui` | `live_tui(hub)`, `live_tui_context(hub)` | Read-only live display; `[tui]` extra (`rich>=13`); lazy import |
| `agent_dashboard/__init__` | Re-exports protocol, renderer, serialization, actions names | Zero asyncio on import |

111 tests, all passing. ruff + mypy strict clean.

---

## Designed, not yet implemented

None. All specified items have been implemented.

---

## Accepted for implementation

None. All accepted items have been implemented.

---

## Deferred (v2)

| Item | Reason |
|------|--------|
| Interactive TUI (textual) | Complex event loop integration; needs `on_action` callback API |
| Replay / event versioning in ScreenHub | Requires explicit consumer requirement; ring-buffer log deferred |
| Sync fallback for non-asyncio consumers | Both current consumers use asyncio |
| Screen families / templates | Framework territory; encodes domain knowledge |
| Fluent screen builder | Coupling cost exceeds syntax benefit |

---

## Explicit non-goals (permanent)

| Item | Reason |
|------|--------|
| Action execution | Library produces text; it does not dispatch |
| Persistence protocol / backend | Each consumer has incompatible persistence needs; no useful unification |
| Transport (WebSocket, SSE, gRPC) | Consumer responsibility |
| Token counting (real tokenizer) | `token_budget` is approximate; no model API calls |
| Field validation (severity, status, kind) | Open-string policy; consumer validates at its own boundary |

---

## Module map (current state)

```
agent_dashboard/
  __init__.py         ← DashboardHighlight, DashboardActionRef, DashboardScreen,
                         SeverityLevel, StatusValue, ViewState,
                         render_screen,
                         screen_to_dict, screen_from_dict,
                         ActionSpec
  protocol.py         ← dataclasses + Literal type aliases
  renderer.py         ← render_screen()
  serialization.py    ← screen_to_dict(), screen_from_dict()
  actions.py          ← ActionSpec
  hub.py              ← ScreenHub                              [explicit import only]
  tui.py              ← live_tui(), live_tui_context()         [extras: tui]
  testing.py          ← make_screen(), screen_diff(),
                         ScreenChangeSummary, hub_context()    [explicit import only]
```

### Import notes

- `hub`, `testing`, and `tui` are **not** re-exported from `__init__` — importing
  them would pull `asyncio` on base import, violating the zero-asyncio guarantee.
  Consumers import them explicitly:
  ```python
  from agent_dashboard.hub import ScreenHub
  from agent_dashboard.testing import make_screen, hub_context
  from agent_dashboard.tui import live_tui_context
  ```
- `tui` requires `pip install agent-dashboard[tui]`.
