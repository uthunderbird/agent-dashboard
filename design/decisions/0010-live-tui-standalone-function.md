# 0010 — live_tui is a standalone function, not a ScreenHub method

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (hub-and-tui.md, context manager hierarchy session)
- **Supersedes:** —
- **Superseded by:** —

## Context

`live_tui` subscribes to a `ScreenHub` and renders each screen update in-place
in the terminal using `rich.Live`. The question was whether `live_tui` should
be a method on `ScreenHub` (e.g. `await hub.start_tui()`) or a standalone
function in a separate module.

## Decision

`live_tui(hub: ScreenHub) -> None` and
`live_tui_context(hub: ScreenHub) -> AsyncGenerator[None, None]`
are standalone async functions in `agent_dashboard.tui`.

`ScreenHub` has no knowledge of TUI. The dependency is one-way:
`tui` imports from `hub`; `hub` does not import from `tui`.

`rich` is imported lazily inside `live_tui()` and `live_tui_context()`, not
at module level. Importing `agent_dashboard.tui` without `rich` installed
does not fail until a function is actually called.

## Alternatives considered

- **`hub.start_tui()` method on ScreenHub** — convenient call site, but
  requires `hub.py` to import `rich` (or to import `tui.py`). Either way,
  `ScreenHub` gains a dependency on optional display machinery. Rejected:
  violates separation of concerns; consumers that never use TUI would
  trigger a `rich` import on every `ScreenHub` instantiation.
- **`live_tui` as a class with `start()`/`stop()`** — adds lifecycle
  management inside TUI itself. Rejected: `live_tui_context` (an
  `@asynccontextmanager`) already handles task lifecycle cleanly without
  a stateful class.

## Consequences

- **Positive:** `ScreenHub` can be imported and used with zero TUI dependencies.
- **Positive:** The `[tui]` extra (`rich`) is only required when `tui.py`
  functions are actually called — not on module import.
- **Positive:** Separation of concerns is explicit in the module map: `hub.py`
  knows nothing about rendering to terminals.
- **Negative:** Call site is slightly more verbose:
  `async with live_tui_context(hub):` vs a hypothetical `async with hub.tui():`.
- **Neutral:** `live_tui_context` is the preferred pattern; bare
  `asyncio.create_task(live_tui(hub))` is supported for consumers that manage
  task lifecycle themselves.

## Notes

`proposals/hub-and-tui.md` § "Context manager map" and § "live_tui and
live_tui_context".
