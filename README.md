# agent-dashboard

Structured workspace screens for LLM agents — a data model and renderer that
turns agent state into a deterministic, token-bounded plain-text prompt block.

## Install

```bash
pip install agent-dashboard
```

Requires Python 3.14+.

## Quickstart

```python
from agent_dashboard import (
    DashboardScreen,
    DashboardHighlight,
    DashboardActionRef,
    ActionSpec,
    render_screen,
)

# Define a reusable action once — bind it to a target per screen.
REPLY = ActionSpec(
    action_id="reply",
    label="Reply",
    kind="action",
    description="Send a reply to the message.",
    requires_approval=True,
)

screen = DashboardScreen(
    dashboard_id="inbox",
    screen_id="turn-1",
    breadcrumb=("Inbox",),
    item_count=3,
    body_lines=(),
    screen_instructions="Reply to the oldest unread message first.",
    highlights=(
        DashboardHighlight(
            highlight_id="msg-1",
            title="Unread messages",
            summary="3 unread messages waiting.",
            severity="high",
            suggested_next_step="Open the oldest unread message.",
        ),
    ),
    screen_actions=(
        REPLY.for_target(
            source_id="inbox",
            item_id="msg-1",
            display_name="Re: Project update",
        ),
    ),
)

rendered = render_screen(screen, token_budget=512)
# Pass `rendered` directly into your LLM prompt.
```

`render_screen()` produces deterministic plain text — same input, same output:

```
Attention items: 3
Breadcrumb: Inbox
View state: collapsed
Reply to the oldest unread message first.
Highlights:
  - [high/active] Unread messages — 3 unread messages waiting.
    next: Open the oldest unread message.
Screen actions:
  - reply: Reply [target=inbox/msg-1:Re: Project update] [requires approval] — Send a reply to the message.
```

The `token_budget` parameter is an approximate token ceiling (4× char multiplier).
Output that exceeds the budget is truncated with `... [truncated]`.

## Core API

All names below are importable directly from `agent_dashboard`.

| Name | What it is |
|------|-----------|
| `DashboardScreen` | Immutable snapshot of what an agent sees — breadcrumb, highlights, actions, body lines, instructions |
| `DashboardHighlight` | A notable item: id, title, summary, severity, optional next step |
| `DashboardActionRef` | A single available action with optional target binding and approval flag |
| `ActionSpec` | Reusable action definition; `.for_target()` produces a bound `DashboardActionRef` |
| `render_screen(screen, *, token_budget)` | Pure function → token-bounded plain-text string |
| `screen_to_dict(screen)` | Serialize to a plain dict (tuple fields → lists) |
| `screen_from_dict(data)` | Deserialize from dict; ignores unknown fields |
| `SeverityLevel`, `StatusValue`, `ViewState` | Literal type aliases for IDE/type-checker feedback; Python does not enforce them at runtime |

### Two action lists

`DashboardScreen` has two action fields:

- **`screen_actions`** — rendered into the plain-text prompt by `render_screen()` under `Screen actions:`. The agent reads these and names one in its structured response.
- **`tool_calls`** — *not* rendered into the prompt. Pass these out-of-band to your model API as native function/tool definitions (e.g. `tools=` in the Anthropic or OpenAI SDK). Both fields hold `DashboardActionRef`; the split is about which rendering channel carries the action, not about severity or approval.

### view_state

`view_state` defaults to `"collapsed"` and appears in the rendered output as `View state: collapsed`. The value `"expanded"` is reserved — you can set it explicitly on a screen, and the renderer will emit `View state: expanded`, but the library does not currently change rendering behaviour based on this field. Future renderer versions may use it to control whether body lines are shown.

## ScreenHub — async reactive streaming

`ScreenHub` lets you publish screens from any thread and subscribe to them
as an async stream. Useful when an agent loop runs in a worker thread and
needs to push state to an async consumer (TUI, WebSocket handler, test fixture).

```python
from agent_dashboard.hub import ScreenHub

async with ScreenHub() as hub:
    # publish from any thread:
    hub.publish(screen, group_id="turn-1")

    # subscribe as an async stream:
    async for screen, group_id in hub.subscribe():
        ...

    # late subscriber? get the last snapshot immediately:
    async for screen, group_id in hub.subscribe_from_latest():
        ...
```

`ScreenHub` is not re-exported from `agent_dashboard` — import it explicitly
to keep the base import free of asyncio.

## Additional modules

| Module | What it provides | Import |
|--------|-----------------|--------|
| `agent_dashboard.testing` | `make_screen()`, `screen_diff()`, assertion helpers, `hub_context()` — test helpers with no pytest coupling | explicit |
| `agent_dashboard.tui` | `live_tui(hub)`, `live_tui_context(hub)` — read-only live terminal display via `rich` | `pip install agent-dashboard[tui]` |

### Testing example

```python
from agent_dashboard.testing import (
    assert_body_contains,
    assert_highlight_ids,
    assert_render_fits_budget,
    make_screen,
    screen_diff,
    hub_context,
)

# Minimal valid screen with sensible defaults — override any field:
screen = make_screen(dashboard_id="inbox", item_count=5)

# Structural diff between two screens:
summary = screen_diff(old_screen, new_screen)
assert summary.item_count_delta == 2

# Author-facing assertions with useful failure messages:
assert_highlight_ids(screen, ("overdue-invoice", "missing-owner"))
assert_body_contains(screen, "Store #1610", "Phase: inspection")
rendered = assert_render_fits_budget(screen, token_budget=512)

# Hub fixture for async tests (works with pytest-asyncio asyncio_mode="auto"):
async with hub_context(initial_screens=[(screen, "turn-1")]) as hub:
    async for s, group_id in hub.subscribe_from_latest():
        ...
```

### Authoring patterns

Keep text and structured data separate. `title`, `summary`, and `body_lines`
are what the agent reads; avoid parsing those fields later to recover IDs,
colors, indexes, or routing hints. Put stable machine-readable data in ids or
`metadata`:

```python
DashboardHighlight(
    highlight_id="figure-3",
    title="Figure 3",
    summary="triangle · red",
    severity="high",
    metadata={"shape": "triangle", "color": "red", "position": 3},
)
```

If a consumer-specific UI needs more state than `DashboardScreen` carries,
keep that adapter in the consuming application. `agent-dashboard` intentionally
models the shared projection boundary; richer HTML, persistence, transport,
and tool execution stay outside the library.

## Design

The library is transport-agnostic and stateless. It does not execute actions,
manage session state, or call any model API. Those concerns belong in the
consuming application.

Full design documentation — boundary decisions, proposals, and glossary — lives
in [`design/`](design/).

Release history lives in [`CHANGELOG.md`](CHANGELOG.md).
