---
title: External developer API for agent-dashboard
status: proposed
created: 2026-04-26
updated: 2026-04-26
---

# External developer API for agent-dashboard

## Purpose

Define what `agent-dashboard` promises to developers who use it — what is
exported, what is guaranteed across versions, what the golden path looks like,
where errors arise and what they say, and what is explicitly not promised.

Audience: developers building consuming applications on top of `agent-dashboard`.
Currently: femtobot (see `boundary.md` for migration guidance) and one internal
corporate project. This document is what a developer from either project should
be able to read and then write their first working builder without access to
femtobot source.

This proposal is the output of a Swarm Mode design session on 2026-04-26. The
decisions below were each contested by named critics; rationale lives inline.

> **Normative language:** The keywords MUST, MUST NOT, MAY, SHOULD, and SHOULD
> NOT in this document are used in conformance with
> [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## Golden path — minimum working example

A developer who has installed `agent-dashboard` and wants to render a screen
for inclusion in an LLM prompt:

```python
from agent_dashboard import DashboardHighlight, DashboardActionRef, DashboardScreen, render_screen

screen = DashboardScreen(
    dashboard_id="inbox",
    screen_id="summary",
    breadcrumb=("Inbox", "Today"),
    item_count=3,
    body_lines=(
        "3 unread messages. 1 flagged. 0 pending approvals.",
    ),
    view_state="collapsed",
    screen_instructions=(
        "Review the highlighted messages and respond to urgent items. "
        "Use a tool_call to reply or forward; use screen_actions to snooze "
        "or dismiss. Do not mark session complete while high-severity items remain."
    ),
    highlights=(
        DashboardHighlight(
            highlight_id="msg-42",
            title="Urgent: contract renewal",
            summary="Alice sent the draft for review.",
            severity="high",
            suggested_next_step="Open thread and review attachment.",
        ),
    ),
    screen_actions=(
        DashboardActionRef(
            action_id="snooze-msg-42",
            label="Snooze for 1 hour",
            kind="snooze",
        ),
    ),
    tool_calls=(
        DashboardActionRef(
            action_id="reply-msg-42",
            label="Reply to Alice",
            kind="send_message",
            description="Compose and send a reply in the thread.",
            requires_approval=True,
        ),
    ),
)

rendered: str = render_screen(screen, token_budget=2000)
# → pass `rendered` as part of the system prompt or user message to your LLM
```

`render_screen()` returns a plain-text string. It is synchronous and has no
side effects. The result is ready to embed in a prompt.

---

## Public surface

The library exports exactly four names from its top-level package:

```python
from agent_dashboard import (
    DashboardHighlight,   # data type
    DashboardActionRef,   # data type
    DashboardScreen,      # data type
    render_screen,        # function
)
```

All four names are stable across 0.x versions once this proposal is accepted.
They will remain stable in 1.0. Additions in 0.x and 1.x minor releases MUST
NOT remove or rename any of these four names.

### `DashboardHighlight`

```python
@dataclass(frozen=True)
class DashboardHighlight:
    highlight_id: str
    title: str
    summary: str
    severity: str
    status: str = "active"
    source_ref: str | None = None
    suggested_next_step: str | None = None
```

A single notable item surfaced within a screen. Highlights are observations,
not actions.

| Field | Purpose | Notes |
|-------|---------|-------|
| `highlight_id` | Opaque identifier | Used by consumers for referencing; not interpreted by the library. |
| `title` | Short display title | Rendered inline with severity and status. |
| `summary` | One-sentence description | Rendered inline after the title. |
| `severity` | Consumer-defined severity level | Open string; library does not validate. Convention: `"high"`, `"medium"`, `"low"`. |
| `status` | Current state of the highlight | Open string; library does not validate. Default `"active"`. |
| `source_ref` | Optional back-reference to the source event | Not rendered; available for consumer use. |
| `suggested_next_step` | Human-readable next-step hint | Rendered on a separate line below the highlight if present. |

### `DashboardActionRef`

```python
@dataclass(frozen=True)
class DashboardActionRef:
    action_id: str
    label: str
    kind: str
    description: str | None = None
    target_source_id: str | None = None
    target_item_id: str | None = None
    target_display_name: str | None = None
    requires_approval: bool = False
    metadata: Mapping[str, Any] | None = None
```

A pointer to an action the agent may take. The library renders action
references; it does not execute them.

| Field | Purpose | Notes |
|-------|---------|-------|
| `action_id` | Opaque action identifier | Rendered as the action's key. The agent uses it when requesting execution. |
| `label` | Human-readable action label | Rendered inline after `action_id`. |
| `kind` | Consumer-defined action subtype | Open string; library does not validate. Use for your own dispatch. |
| `description` | Optional longer description | Appended to the rendered line if present. |
| `target_source_id` | Source scope of the target | First component of the rendered target suffix. |
| `target_item_id` | Item identity within the source scope | Second component. |
| `target_display_name` | Human-readable target label | Third component. |
| `requires_approval` | Approval signal for the agent | When `True`, renderer appends `[requires approval]` to the action line. Default `False`. |
| `metadata` | Uninterpreted pass-through | The renderer never reads this field. Use for consumer-specific typed data that does not need to appear in rendered output. |

Target suffix rendering: `[target={target_source_id}/{target_item_id or '-'}:{target_display_name or '-'}]`.
The suffix is omitted entirely if `target_source_id is None`.

`[requires approval]` is appended after the target suffix and before the
description suffix, only when `requires_approval=True`.

**Convention:** set `requires_approval=True` on all `tool_calls` that have
external side effects or affect third parties. `screen_actions` by definition
have no external effects — leave `requires_approval=False` (the default).
The library does not enforce this convention; your application does.

**On `metadata`:** the library promises only that it will never read, modify,
or render `metadata`. It is purely a structured side-channel for consumer
use. If you need typed fields beyond what `DashboardActionRef` provides,
define your own dataclass and convert with a `.to_library()` method before
passing to `render_screen()`. See `boundary.md` Decision 2.

### `DashboardScreen`

```python
@dataclass(frozen=True)
class DashboardScreen:
    dashboard_id: str
    screen_id: str
    breadcrumb: tuple[str, ...]
    item_count: int
    body_lines: tuple[str, ...]
    view_state: Literal["collapsed", "expanded"] = "collapsed"
    screen_instructions: str | None = None
    highlights: tuple[DashboardHighlight, ...] = field(default_factory=tuple)
    screen_actions: tuple[DashboardActionRef, ...] = field(default_factory=tuple)
    tool_calls: tuple[DashboardActionRef, ...] = field(default_factory=tuple)
```

The unit of rendering. An immutable snapshot of what the agent "sees" at a
given moment.

| Field | Purpose | Notes |
|-------|---------|-------|
| `dashboard_id` | Identifies the dashboard family | e.g. `"inbox"`, `"tasks"`. Consumer-defined. |
| `screen_id` | Identifies the screen within the dashboard | e.g. `"summary"`, `"detail"`. Consumer-defined. |
| `breadcrumb` | Navigation path from root to current screen | Rendered as `A > B > C`. May be empty. |
| `item_count` | Total item count at this view | Rendered on the first line. Builder responsibility to compute. |
| `body_lines` | Main content lines | Plain text only. Rendered after highlights, before actions. |
| `view_state` | Current display mode | `"collapsed"` or `"expanded"`. Informational only — see below. |
| `screen_instructions` | Task framing for the agent | Rendered verbatim between `View state:` and `Highlights:`. Optional. See below. |
| `highlights` | Notable items to surface | Rendered as a structured list before `body_lines`. |
| `screen_actions` | Local, side-effect-free actions | No external effects; no approval needed. |
| `tool_calls` | External actions with potential side effects | May require consumer-side approval before execution. |

**`screen_instructions` — when and how to use.** This field lets the builder
give the agent a brief operating context for the current screen: what the
primary goal is, what to prioritize, what to avoid. It is rendered as the
first content block after the header, so the agent reads it before highlights
and actions. Use it when:

- The screen family is new or unfamiliar (first visit, no bootstrap skill).
- The screen has non-obvious action semantics (e.g. order of operations matters).
- The agent is operating on a custom dashboard with no SKILL.md in bootstrap.

Keep `screen_instructions` short — one to three sentences. It is not a
tutorial; it is a context-setter. Detailed operating guidance belongs in a
SKILL.md bootstrap skill. Leave it `None` for well-known screens where the
agent already has context from bootstrap or recent session actions.

Example:
```python
screen_instructions=(
    "You are reviewing incoming tasks. Prioritise items with severity=high. "
    "Use a tool_call to complete or delegate tasks; use screen_actions to "
    "dismiss or snooze. Do not emit session_complete while high-severity "
    "tasks remain unaddressed."
),
```

**`view_state` is informational.** The renderer prints `View state: collapsed`
(or `expanded`) in its output, but does not change what it includes based on
this field. Whether a screen should show abbreviated or full content is the
builder's responsibility: build a different `DashboardScreen` for each mode.
The field exists so the agent reading the rendered output sees the current
mode as context.

**`screen_actions` vs `tool_calls`.** The renderer formats both lists
identically. The distinction is semantic and consumer-enforced: screen actions
MUST have no external side effects; tool calls MAY have external side effects
and SHOULD be routed through your application's approval boundary before
execution. Mark side-effecting tool calls with `requires_approval=True` so the
agent has an explicit signal. The library does not enforce either constraint —
your application does.

### `render_screen(screen, *, token_budget=4000) -> str`

```python
def render_screen(
    screen: DashboardScreen,
    *,
    token_budget: int = 4000,
) -> str:
    ...
```

Renders a `DashboardScreen` to a plain-text string.

**Promises:**
- Pure function: no side effects, no I/O, no global state mutation.
- Deterministic: same `(screen, token_budget)` → same output, always.
- Never raises: does not raise for any combination of valid Python inputs,
  including empty collections, zero or negative `token_budget`, or very large
  screens.

**`token_budget`:** approximate upper bound on output size. Internally
converted to `char_budget = max(32, token_budget * 4)`. The 4× multiplier
approximates characters-per-token for typical LLM tokenizers; it is not
exact. `token_budget=0` or negative values result in a 32-character budget.

**Output order:** header fields → `screen_instructions` → highlights → body lines → screen actions
→ tool calls. Each section header (`Highlights:`, `Screen actions:`,
`Tool calls:`) is omitted if the corresponding collection is empty.
`screen_instructions` is omitted if `None`.

**Truncation:** if the full rendered string exceeds `char_budget`, the output
is truncated at character position `char_budget - len("... [truncated]") - 1`,
stripped of trailing whitespace, and the marker `... [truncated]` is appended
on a new line. Truncation may cut mid-line. The truncation marker string is
not yet a public constant; do not depend on its exact value in 0.x.

---

## Promises (stable across versions)

> Additions in minor versions MUST preserve all promises below. Removing or
> narrowing any promise is a major-version breaking change.

**P-1. Four stable exports.** The package exports exactly
`DashboardHighlight`, `DashboardActionRef`, `DashboardScreen`, and
`render_screen`. These names MUST NOT be removed or renamed in any 0.x or
1.x release.

**P-2. Frozen dataclasses.** All three data types are `frozen=True`. No field
can be reassigned after construction. Code that relies on mutability of these
types has undefined behavior.

**P-3. All-tuple collections.** `breadcrumb`, `body_lines`, `highlights`,
`screen_actions`, and `tool_calls` are `tuple[...]` types. They are always
safe to iterate multiple times.

**P-3a. Conditional hashability.** A `DashboardScreen` is hashable when all
fields it contains are hashable. `DashboardActionRef.metadata` is typed
`Mapping[str, Any] | None` and accepts unhashable values such as `dict`. A
`DashboardActionRef` with `metadata={"key": "val"}` (or any other unhashable
value) is itself unhashable, and a `DashboardScreen` containing such an
instance in `screen_actions` or `tool_calls` is also unhashable. Callers who
need hashable instances must use only hashable `metadata` values (e.g. `None`,
a frozen dataclass, a `NamedTuple`). See also ADR-0001.

**P-4. `render_screen` purity.** `render_screen()` is a pure function. It
MUST NOT perform I/O, mutate any argument, or read or write any global or
module-level state.

**P-5. `render_screen` never raises.** `render_screen()` MUST NOT raise for
any valid Python input. "Valid" means: `screen` is a `DashboardScreen`
instance, `token_budget` is an `int`. Passing non-`DashboardScreen` objects
or non-`int` budgets is undefined behavior.

**P-6. `metadata` opacity.** The renderer MUST NOT read, render, or modify
`DashboardActionRef.metadata`. Consumers may store any value in `metadata`
and it will pass through unchanged.

**P-7. `view_state` informational.** The renderer MUST NOT alter what
sections it renders based on `view_state`. It MUST print `view_state` as a
string in the output header.

**P-8. Rendering symmetry.** `screen_actions` and `tool_calls` MUST be
rendered with identical formatting logic.

**P-9. No dependency on consuming applications.** The library MUST NOT import
any module from any consuming application. The dependency graph is one-way.

**P-10. Additive-only field additions.** New optional fields added to
`DashboardHighlight`, `DashboardActionRef`, or `DashboardScreen` in future
releases MUST have defaults. Code that constructs these types with keyword
arguments (the recommended style) MUST continue to work without modification.

**P-11. `screen_instructions` verbatim rendering.** If
`DashboardScreen.screen_instructions` is not `None`, `render_screen()` MUST
include it verbatim in the output between the `View state:` line and the
`Highlights:` section. The renderer MUST NOT modify, reformat, or
independently truncate `screen_instructions`.

**P-12. `requires_approval` rendering.** When
`DashboardActionRef.requires_approval` is `True`, `render_screen()` MUST
append the string `[requires approval]` to that action's rendered line. When
`False` (the default), no such suffix is appended. The exact marker string
`[requires approval]` is a 0.x promise; changing it is a breaking change.

---

## Non-promises

The library explicitly does not promise:

**NP-1. Token accuracy.** `token_budget` is an integer hint. The library does
not call any LLM API, tokenizer, or model. The 4× char-per-token multiplier
is approximate.

**NP-2. Content decisions.** The library does not decide what to put in
`body_lines`, which highlights to include, or which actions to expose. That is
the builder's job.

**NP-3. Action execution.** The library does not dispatch `screen_actions` or
`tool_calls`. It renders them as text. Execution is the consuming
application's responsibility.

**NP-4. Approval enforcement.** The library does not enforce that `tool_calls`
pass through an approval boundary, and does not treat `requires_approval=True`
as a gate. The flag is rendered as a text hint; enforcement is the consuming
application's responsibility.

**NP-5. Field validation.** The library does not validate `severity`,
`status`, `kind`, `dashboard_id`, `screen_id`, or any other open-string
field. Invalid values render as-is.

**NP-6. Truncation marker stability in 0.x.** The truncation marker string
`"... [truncated]"` is not a public constant in 0.x. Do not match against it
in consumer code. It will be promoted to a public constant before 1.0.

**NP-7. Behavioral `view_state`.** The library does not promise to ever add
behavioral rendering based on `view_state`. Adding it would be a semantic
change; if it is ever added, it will be under a separate opt-in mechanism,
not a change to the `view_state` field semantics.

**NP-8. Structured errors.** `render_screen()` does not raise typed
exceptions for semantic problems (e.g. `item_count` mismatching the actual
highlights count). Semantic validation is caller responsibility.

**NP-9. `screen_instructions` interpretation.** The library does not parse,
validate, or act on the content of `screen_instructions`. Correctness of the
instructions (task framing, action guidance, anti-patterns) is builder
responsibility.

**NP-10. `navigation_policy` field.** The library does not provide a
`navigation_policy` field on `DashboardScreen` or any dynamic per-screen
policy injection mechanism. Dynamic navigation policy that adapts to session
state (e.g. pending attention, recent actions) belongs in the consuming
application's session assembly layer. See `notes/screen-agent-ux.md` M3.

---

## Error surface

`render_screen()` is documented to never raise (P-5). The following describes
what happens for common edge cases instead of errors:

| Condition | Behaviour |
|-----------|-----------|
| `token_budget=0` or negative | Effective budget is 32 characters; output is heavily truncated. |
| `body_lines=()` | Body section is empty; highlights and actions still render. |
| `highlights=()` | `Highlights:` section header is omitted entirely. |
| `screen_actions=()` | `Screen actions:` section header is omitted entirely. |
| `tool_calls=()` | `Tool calls:` section header is omitted entirely. |
| `breadcrumb=()` | Renders `Breadcrumb: ` (empty, no separator). |
| `item_count=0` | Renders `Attention items: 0`. |
| Very large screen | Output is truncated at `char_budget` with the truncation marker. |
| `target_source_id=None` | Target suffix `[target=...]` is omitted for that action. |
| `description=None` | Description suffix ` — ...` is omitted for that action. |
| `suggested_next_step=None` | `next:` line is omitted for that highlight. |
| `screen_instructions=None` | Instructions block is omitted entirely; no blank line inserted. |
| `requires_approval=False` | No `[requires approval]` suffix appended (default behaviour). |
| `requires_approval=True` | `[requires approval]` appended after target suffix, before description. |

The only way `render_screen()` can raise is if the caller passes an object
that is not a `DashboardScreen` instance, or if a field contains an object
whose `__str__` or `__format__` raises. Both are caller bugs, not library
errors.

---

## DX rubric

Falsifiable criteria for the developer experience. Each criterion either
passes or fails; vague claims are not rubric entries.

**R-1.** A developer with no prior `agent-dashboard` knowledge can construct
a `DashboardScreen` and call `render_screen()` using only the type signatures
and field names, without reading source code.

**R-2.** The rendered output of the golden path example contains the strings
`"Urgent: contract renewal"`, `"snooze-msg-42"`, and `"reply-msg-42"` in
that order. *Test: render the golden path screen; assert substring presence
and order.*

**R-3.** `render_screen(screen, token_budget=10)` returns a string of at most
`max(32, 10 * 4) = 40` characters plus the truncation marker, and does not
raise. *Test: call with budget=10; assert no exception; assert len ≤ 40 +
len("... [truncated]") + 1.*

**R-4.** `render_screen(screen, token_budget=0)` does not raise and returns a
non-empty string. *Test: call with budget=0; assert no exception; assert
len(result) > 0.*

**R-5.** Passing `metadata={"routing_key": "x", "priority": 1}` on a
`DashboardActionRef` does not cause `metadata` to appear anywhere in
`render_screen()` output. *Test: assert `"routing_key"` not in
render_screen(...).*

**R-6.** A `DashboardScreen` with `screen_actions=()` and `tool_calls=()`
renders without the `Screen actions:` or `Tool calls:` section headers.
*Test: assert `"Screen actions:"` not in output.*

**R-7.** `view_state="collapsed"` and `view_state="expanded"` produce outputs
that differ only in the `View state:` line, given identical other fields.
*Test: render same screen with both values; diff the outputs; assert only the
`View state:` line differs.*

**R-8.** Constructing `DashboardActionRef` with only `action_id`, `label`,
and `kind` (all other fields at defaults) renders a valid action line without
target suffix or description suffix. *Test: assert `"[target="` not in output.*

**R-9.** All three data types are hashable and can be used as `dict` keys or
`set` members. *Test: `hash(screen)` does not raise.*

**R-10.** The public surface — `DashboardHighlight`, `DashboardActionRef`,
`DashboardScreen`, `render_screen` — is importable from the top-level package
without submodule imports. *Test: `from agent_dashboard import DashboardHighlight,
DashboardActionRef, DashboardScreen, render_screen` succeeds.*

**R-11.** A `DashboardScreen` with `screen_instructions="Do X before Y."` renders
the string `"Do X before Y."` verbatim between the `View state:` line and the
`Highlights:` section. *Test: assert `"Do X before Y."` in output; assert it
appears after `"View state:"` and before `"Highlights:"`.*

**R-12.** A `DashboardActionRef` with `requires_approval=True` renders with
`[requires approval]` in its line; one with `requires_approval=False` (default)
does not. *Test: render screen with one approved and one non-approved action;
assert `"[requires approval]"` appears exactly once in the output, on the correct
action line.*

---

## How to build a screen: builder pattern

The library does not provide builders. Consumers write builder functions that
assemble domain data into `DashboardScreen` instances. A builder should:

1. Accept domain objects (database records, event queues, API responses).
2. Produce `DashboardHighlight` instances for notable items.
3. Produce `DashboardActionRef` instances for available actions, partitioned
   into local (`screen_actions`) and external (`tool_calls`).
4. Assemble a `DashboardScreen` and return it.
5. Call `render_screen()` at the point where the rendered string is needed.

Builders are pure functions where possible. They should not perform I/O
themselves; I/O belongs in the calling layer, which passes resolved data to
the builder.

Example skeleton:

```python
from agent_dashboard import (
    DashboardHighlight,
    DashboardActionRef,
    DashboardScreen,
    render_screen,
)

def build_task_screen(tasks: list[Task], token_budget: int = 3000) -> str:
    highlights = tuple(
        DashboardHighlight(
            highlight_id=f"task-{task.id}",
            title=task.title,
            summary=task.description[:120],
            severity="high" if task.overdue else "medium",
            suggested_next_step="Review and update status." if task.overdue else None,
        )
        for task in tasks[:10]  # surface top 10
    )

    screen_actions = (
        DashboardActionRef(
            action_id="mark-all-seen",
            label="Mark all as seen",
            kind="mark_seen",
        ),
    )

    tool_calls = tuple(
        DashboardActionRef(
            action_id=f"complete-task-{task.id}",
            label=f"Complete: {task.title}",
            kind="complete_task",
            target_source_id="tasks",
            target_item_id=str(task.id),
            target_display_name=task.title,
            requires_approval=True,
        )
        for task in tasks
        if not task.completed
    )

    screen = DashboardScreen(
        dashboard_id="tasks",
        screen_id="overview",
        breadcrumb=("Tasks", "Overview"),
        item_count=len(tasks),
        body_lines=(
            f"{sum(t.overdue for t in tasks)} overdue.",
            f"{sum(not t.completed for t in tasks)} in progress.",
        ),
        view_state="collapsed",
        screen_instructions=(
            "Review overdue tasks first (severity=high). "
            "Use complete_task tool_call to finish a task — this requires approval. "
            "Use mark-all-seen screen_action to dismiss the view without external effect."
        ) if tasks else None,
        highlights=highlights,
        screen_actions=screen_actions,
        tool_calls=tool_calls,
    )

    return render_screen(screen, token_budget=token_budget)
```

---

## Versioning

This library follows [Semantic Versioning](https://semver.org/).

- **Patch releases (0.x.y):** bug fixes only. No API changes.
- **Minor releases (0.x+1.0):** additive changes only. New optional fields
  with defaults, new exports, behavioral fixes that do not alter the output
  of existing correct callers.
- **Major releases (1.0.0, 2.0.0):** may include breaking changes. Removals,
  renames, narrowing of promises, or behavioral changes that alter existing
  output are reserved for major releases.

Fields added in minor releases MUST have defaults so that existing
keyword-argument construction continues to work (P-10).

---

## Relation to `boundary.md`

`boundary.md` (`design/proposals/boundary.md`) is the companion document to
this one. It answers: *why is the boundary here, and not one step further in
either direction?* Read `boundary.md` for:

- The rationale behind each coupling decision (what was rejected and why).
- Library invariants with implementation-level precision.
- The renderer's exact truncation algorithm.
- Migration guidance for femtobot.

This document (`external-dev-api.md`) answers: *what do I get as a
developer?* It is developer-facing and normative. `boundary.md` is
contributor-facing and descriptive. They cross-reference each other and MUST
NOT contradict each other; if they do, this document takes precedence for
normative claims.

---

## Promotion to ADR

When this proposal is accepted alongside `boundary.md`:

1. Distill `boundary.md` into `decisions/0001-library-boundary.md` (ADR).
   Drop migration guidance into `notes/femtobot-migration.md`.
2. Distill the promises and non-promises from this document into
   `decisions/0002-external-dev-api.md` (ADR). Keep the golden path,
   DX rubric, and builder pattern in this file as a living developer guide
   (move it to `dx/developer-guide.md`).
3. Update `proposals/README.md` to remove both proposals from the index.
4. Update `decisions/README.md` to add both ADRs.
5. Implement: copy `protocol.py` and `renderer.py` from femtobot, strip
   femtobot imports, land with tests verifying R-1 through R-10.
