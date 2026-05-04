---
title: ScreenHub and TUI — reactive screen streaming design
status: proposed
created: 2026-04-26
updated: 2026-04-26
revision: 2
---

# ScreenHub and TUI — reactive screen streaming design

## Purpose

Define the public API and design decisions for reactive screen streaming
(`ScreenHub`) and the terminal UI helper (`live_tui`). This document is the
output of a Swarm Mode design session and covers what the library adds, what
stays in consuming applications, and the implementation constraints.

---

## What the library adds

Three opt-in modules, each independently importable:

```
agent_dashboard/
  __init__.py     ← unchanged: DashboardHighlight, DashboardActionRef,
                              DashboardScreen, render_screen
  protocol.py     ← unchanged
  renderer.py     ← unchanged
  hub.py          ← ScreenHub  (new; NOT re-exported from __init__)
  tui.py          ← live_tui() (new; optional extra [tui], requires rich)
```

`ScreenHub` is not re-exported from `__init__.py`. Consumers import it
explicitly:

```python
from agent_dashboard.hub import ScreenHub
```

This preserves the zero-asyncio guarantee of the base import: code that only
uses `render_screen()` never touches asyncio.

---

## ScreenHub — public API

```python
class ScreenHub:
    def __init__(
        self,
        *,
        maxsize: int = 16,
        overflow: Literal["drop_newest", "drop_oldest", "raise"] = "drop_newest",
    ) -> None: ...

    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind Hub to an event loop. Called automatically on first subscribe()."""

    def publish(
        self,
        screen: DashboardScreen,
        *,
        group_id: str | None = None,
    ) -> None:
        """
        Thread-safe. May be called from any thread, including threads outside
        the asyncio event loop.

        group_id optionally tags this snapshot with a caller-defined grouping
        key (e.g. a turn identifier, batch id, or request id). group_id=None
        means the snapshot belongs to no named group. Subscribers receive the
        group_id alongside the snapshot.

        Implementation: loop.call_soon_threadsafe() for each subscriber queue.
        Does NOT use thread pool executor — publish() is a microsecond-scale
        operation with no I/O; executor overhead would exceed the work itself.

        Raises RuntimeError if Hub is closed or if no event loop is attached
        (i.e. subscribe() has never been called and attach() was not called
        explicitly).
        """

    async def subscribe(self) -> AsyncGenerator[tuple[DashboardScreen, str | None], None]:
        """
        Yields (screen, group_id) pairs. group_id is the value passed to
        publish(), or None if none was given.

        One Queue per subscriber, bounded by maxsize. Attaches to the running
        event loop on first call if attach() was not called explicitly.

        Terminates (StopAsyncIteration) when the Hub is closed.
        """

    @property
    def dropped_count(self) -> int:
        """Cumulative count of events dropped due to full subscriber queues."""

    def reset_dropped(self) -> None:
        """Reset dropped_count to zero."""

    async def aclose(self) -> None:
        """Notify all subscribers and release resources."""

    async def __aenter__(self) -> "ScreenHub":
        """Attach to the running event loop. Enables thread-safe publish() immediately."""
        self._loop = asyncio.get_running_loop()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Call aclose(): send sentinel to all subscribers, release resources."""
```

### Event model

**Event = full `DashboardScreen` snapshot.**

No diffs. Computing deltas between two snapshots is consumer responsibility.
The wire format for frontends, diff computation for WebSocket optimisation,
and replay/versioning on reconnect are all consumer concerns.

Rationale:
- Diff semantics on a hierarchical object are ambiguous (replace? reorder? add?).
- Diff requires Hub to store "previous" state — an additional stateful concern
  with no library-level benefit.
- A consumer that needs deltas compares two consecutive snapshots itself.

### Overflow policy

`overflow` is set at Hub construction and applies to all subscribers equally:

| Value | Behaviour |
|-------|-----------|
| `"drop_newest"` (default) | Silently discard the incoming screen if any subscriber queue is full. Increments `dropped_count`. |
| `"drop_oldest"` | Discard the oldest item in the full queue before enqueuing the new screen. |
| `"raise"` | Raise `asyncio.QueueFull` from `publish()`. |

Default `"drop_newest"` is appropriate for debug TUI (losing a frame is ok)
and for high-frequency publishing where the consumer is the bottleneck.

### Loop attachment

Hub must be attached to an asyncio event loop before `publish()` can use
`call_soon_threadsafe()`. Attachment happens in one of three ways, in order of
preference:

1. **Via context manager (preferred)** — `async with ScreenHub() as hub:`
   calls `__aenter__`, which runs `asyncio.get_running_loop()` at entry.
   `publish()` is safe to call from any thread immediately after.
2. **Automatic on first subscribe** — if `__aenter__` was not used, the first
   `subscribe()` call attaches the loop. Works when Hub is used without `async
   with`, but means `publish()` cannot safely be called before the first
   subscriber connects.
3. **Explicit** — `hub.attach(loop)` for edge cases where neither of the above
   is possible.

If `publish()` is called before attachment, it raises `RuntimeError`. Silent
failure is not acceptable here.

### Lifecycle

Hub is a context manager:

```python
async with ScreenHub() as hub:
    # hub is open; subscribers receive events
# hub.aclose() called automatically; subscribers get StopAsyncIteration
```

`aclose()` can also be called explicitly. Calling `publish()` after `aclose()`
raises `RuntimeError`.

---

## live_tui and live_tui_context — public API (optional extra [tui])

Requires: `pip install agent-dashboard[tui]` (adds `rich` as dependency).

`rich` is imported lazily inside these functions; importing `agent_dashboard.tui`
without `rich` installed does not fail — the error surfaces at the first call.

```python
async def live_tui(hub: ScreenHub) -> None:
    """
    Subscribe to hub and render each (screen, group_id) snapshot in-place in
    the terminal using rich.Live. Runs until hub is closed.

    Uses render_screen() to produce the text representation, wrapped in a
    rich.Panel. group_id is shown in the panel title when present.
    """

@asynccontextmanager
async def live_tui_context(hub: ScreenHub) -> AsyncGenerator[None, None]:
    """
    Async context manager that starts live_tui as a background task and
    cancels it cleanly on exit.

    Preferred over bare asyncio.create_task(live_tui(hub)) because it
    handles CancelledError and guarantees task cleanup on block exit,
    including on exception.
    """
```

Usage patterns:

```python
from agent_dashboard.hub import ScreenHub
from agent_dashboard.tui import live_tui_context

# Preferred: context manager handles task lifecycle
async def main():
    async with ScreenHub() as hub:
        async with live_tui_context(hub):
            await agent.run(hub)

# Manual: caller owns task lifecycle
async def main():
    async with ScreenHub() as hub:
        task = asyncio.create_task(live_tui(hub))
        await agent.run(hub)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
```

### TUI scope

`live_tui` is read-only. It displays the current screen state; it does not
provide action invocation. Interactive TUI (triggering actions from the
terminal) is deferred to v2 and requires a separate `on_action` callback API.

Rationale: action invocation expands the library contract to "agent controller"
territory. The read-only TUI is a self-contained debugging aid.

---

## What stays in consuming applications

| Concern | Reason |
|---------|--------|
| WebSocket / SSE / gRPC transport | Transport layer is consumer responsibility |
| JSON serialisation for frontends | `dataclasses.asdict()` sufficient; consumer adds custom encoder if needed |
| Diff / delta computation | Consumer compares two consecutive snapshots |
| Replay / versioning on reconnect | Deferred v2; requires explicit consumer requirement |
| Interactive TUI (textual) | Deferred v2; complex event loop integration |
| Sync fallback for non-asyncio consumers | Deferred v2; assumption A3: both current consumers use asyncio |
| Action invocation from TUI | Out of scope for library |
| Session context manager | "Session" is a consuming-app concept. femtobot uses `async def` + task cancellation, not a CM. The library has no model of sessions. |
| Turn / batch context manager (`hub.turn()`) | "Turn" is femtobot-specific vocabulary. A general library CM would impose turn semantics on consumers whose execution model uses different units (batch, request, job). Use `group_id` on `publish()` instead. |

---

## Context manager map

Two context managers are provided by the library:

| CM | Module | Type | Responsibility |
|----|--------|------|---------------|
| `ScreenHub` | `hub.py` | `async with` | Loop attachment on enter; subscriber cleanup + sentinel on exit |
| `live_tui_context(hub)` | `tui.py` | `@asynccontextmanager` | TUI task creation on enter; `cancel()` + `await` on exit |

`live_tui_context` is intentionally a standalone function, not a method on
`ScreenHub`. Hub has no knowledge of TUI; TUI depends on Hub, not the reverse.

---

## Design constraints (unchanged)

All existing constraints from `boundary.md` hold:

- `render_screen()` remains a pure function with no knowledge of Hub.
- All three dataclasses remain frozen and immutable.
- `__init__.py` does not import asyncio; base import has no async overhead.
- ScreenHub is opt-in; it is not part of the render pipeline.
- One-way dependency: Hub imports from `agent_dashboard.protocol`, never from
  any consuming application.

---

## Implementation notes

**Thread-safe publish.** `publish()` uses `loop.call_soon_threadsafe()` for
each subscriber queue, not `run_in_executor`. Rationale: `publish()` is a
microsecond-scale operation (no I/O, no blocking). `run_in_executor` adds
thread pool overhead that exceeds the work itself. `call_soon_threadsafe()` is
the correct asyncio primitive for "schedule work in the event loop from another
thread."

**dropped_count.** Silent drops under `"drop_newest"` are counted and exposed
via `hub.dropped_count`. Consumers polling for debug information can read this
value. `reset_dropped()` resets the counter.

**Sentinel pattern.** `aclose()` places a sentinel object into all subscriber
queues. Subscriber generators detect the sentinel and raise
`StopAsyncIteration`. This avoids `asyncio.Event` or `asyncio.Condition`
overhead for shutdown signalling.

**group_id semantics.** `publish(screen, group_id="turn-42")` tags the
snapshot for downstream consumers (frontend, TUI, tests). `group_id=None`
means "no group". The name `group_id` was chosen over `turn_id` deliberately:
it is neutral to the consuming app's execution model (turn, batch, request,
job). Femtobot maps its `turn_count` to `group_id`; the corporate consumer
maps its own unit.

**lazy rich import.** `tui.py` imports `rich` inside `live_tui()` and
`live_tui_context()`, not at module level. Importing `agent_dashboard.tui`
without `rich` installed does not raise `ImportError` until a function is
called. This matches standard practice for optional-dependency modules.

---

## Deferred items (v2)

- **Replay / event versioning:** consumers reconnecting to a Hub cannot
  recover missed events. v2 may introduce an optional ring-buffer log.
- **Interactive TUI:** `live_tui` with action-button invocation via textual.
  Requires `on_action(action_id: str) -> None` callback API.
- **Sync fallback:** `publish_sync()` / sync context manager for consumers not
  running asyncio.
