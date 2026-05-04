---
title: Library boundary specification for agent-dashboard
status: proposed
created: 2026-04-26
updated: 2026-04-26
---

# Library boundary specification for agent-dashboard

## Purpose

Define what enters `agent-dashboard` as a public library contract, what
explicitly stays in consuming applications, and the coupling decisions that
draw the boundary. This document is the design baseline that must be approved
before any implementation work begins.

Audience: contributors to `agent-dashboard` and authors of consuming
applications (currently: femtobot, and one internal corporate project).

This proposal is the output of two Swarm Mode design sessions grounded in
the existing femtobot codebase. Each coupling decision below was contested
and the rationale is stated inline. Rejected alternatives are preserved.

---

## Background

`agent-dashboard` is extracted from femtobot's
`src/femtobot/dashboards/{protocol,renderer}.py`. The original code served a
single consumer (femtobot) and therefore accumulated femtobot-specific types
in its core protocol. A second consumer now exists; a clean boundary must be
established before extraction.

The parallel library `promptstrings` (at `../promptstrings/`) serves as the
structural template for this repository.

---

## What enters the library

### `agent_dashboard.protocol`

Three frozen dataclasses forming the core data model:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class DashboardHighlight:
    highlight_id: str
    title: str
    summary: str
    severity: str
    status: str = "active"
    source_ref: str | None = None
    suggested_next_step: str | None = None


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

### `agent_dashboard.renderer`

One public function:

```python
def render_screen(screen: DashboardScreen, *, token_budget: int = 4000) -> str:
    ...
```

See "Renderer semantics" below for the full behavioral specification.

### Package exports (`agent_dashboard/__init__.py`)

All four names are re-exported from the top-level package:

```python
from agent_dashboard.protocol import (
    DashboardHighlight,
    DashboardActionRef,
    DashboardScreen,
)
from agent_dashboard.renderer import render_screen

__all__ = [
    "DashboardHighlight",
    "DashboardActionRef",
    "DashboardScreen",
    "render_screen",
]
```

---

## Library invariants

These properties hold for any correct implementation of the library. Code
review and tests should verify them; violation of any invariant is a bug, not
a design choice.

**I-1. Purity.** `render_screen()` is a pure function. It performs no I/O,
has no observable side effects, reads no global state, and does not mutate
its arguments. Same input → same output, always.

**I-2. Immutability.** All three protocol types are `frozen=True` dataclasses.
All collection fields (`breadcrumb`, `body_lines`, `highlights`,
`screen_actions`, `tool_calls`) are `tuple[...]`. No field on any library type
is mutable after construction.

**I-3. Truncation determinism.** For a given `(screen, token_budget)` pair,
`render_screen()` returns the same string on every call. Truncation is
character-position-based, not hash-based or random.

**I-4. No consumer imports.** Library code (`protocol.py`, `renderer.py`)
imports nothing from any consuming application. The dependency graph is
one-directional: consumer → library. Any import of a consumer-side module
inside the library is a boundary violation.

**I-5. Renderer opacity.** `render_screen()` does not inspect or interpret
`DashboardActionRef.metadata`. It renders the action reference's `action_id`,
`label`, `target_source_id`, `target_item_id`, `target_display_name`,
`requires_approval`, and `description` fields only. `metadata` is carried
through the data model silently.

**I-6. `view_state` is informational.** `render_screen()` prints `view_state`
as a string in its output (`View state: collapsed`) but does not alter what
it renders based on it. Whether to include `body_lines` in a given screen,
or which highlights to surface, is the builder's responsibility. The renderer
is a dump engine: it serializes what it receives.

**I-7. Rendering symmetry.** `render_screen()` renders `screen_actions` and
`tool_calls` with identical formatting logic. The semantic distinction between
the two lists (local vs external effects) is meaningful to consumers but
invisible to the renderer. See Decision 3 for why the distinction exists
despite rendering symmetry.

**I-8. `screen_instructions` verbatim pass-through.** If
`DashboardScreen.screen_instructions` is not `None`, `render_screen()` inserts
it verbatim as a block of text between the `View state:` line and the
`Highlights:` section. The renderer does not parse, reformat, or truncate
`screen_instructions` independently — it is subject to the same overall
character-budget truncation as the rest of the output.

**I-9. `requires_approval` is a rendering flag, not an enforcement point.**
`render_screen()` appends `[requires approval]` to the rendered line of any
`DashboardActionRef` where `requires_approval=True`. The library does not
block, gate, or otherwise act on this flag. Enforcement of the approval
semantics is the consuming application's responsibility.

---

## Renderer semantics

### Output structure

`render_screen()` produces a newline-joined plain-text string with this
section order:

```
Attention items: {item_count}
Breadcrumb: {breadcrumb[0]} > {breadcrumb[1]} > ...
View state: {view_state}
{screen_instructions}                    ← only if present; rendered as-is after View state
Highlights:
  - [{severity}/{status}] {title} — {summary}
    next: {suggested_next_step}          ← only if present
  ...
{body_lines[0]}
{body_lines[1]}
...
Screen actions:                          ← section omitted if screen_actions is empty
  - {action_id}: {label} [target=...] [requires approval] — {description}
  ...                                    ← [requires approval] only if requires_approval=True
Tool calls:                              ← section omitted if tool_calls is empty
  - {action_id}: {label} [target=...] [requires approval] — {description}
  ...
```

Target suffix format: `[target={target_source_id}/{target_item_id or '-'}:{target_display_name or '-'}]`.
The suffix is omitted entirely if `target_source_id` is `None`.

`description` suffix (` — {description}`) is omitted if `description` is `None`.

`[requires approval]` suffix is appended after the target suffix (if any) and
before the description suffix, only when `requires_approval=True`.

### Truncation algorithm

```
char_budget = max(32, token_budget * 4)
if len(rendered) <= char_budget:
    return rendered
cutoff = max(0, char_budget - len("... [truncated]") - 1)
return rendered[:cutoff].rstrip() + "\n... [truncated]"
```

Key properties:
- The minimum effective budget is 32 characters regardless of `token_budget`.
- Truncation cuts the concatenated output string at `cutoff`, not at a line
  boundary. The truncation marker `... [truncated]` is always on its own line.
- `token_budget` is treated as an approximate token count. The 4× multiplier
  (`char_budget = token_budget * 4`) approximates characters-per-token for
  typical LLM tokenizers. It is not exact and should not be treated as such.
- Negative or zero `token_budget` is not a precondition violation; the
  minimum budget of 32 chars applies.

### What the renderer does not do

- Does not interpret `metadata` on any type.
- Does not change output based on `view_state` value.
- Does not reorder highlights, actions, or body lines.
- Does not validate `severity`, `status`, or `kind` field values.
- Does not raise exceptions for empty or unusual inputs (empty `body_lines`,
  zero `item_count`, empty `highlights`, `token_budget=0`).
- Does not interpret `screen_instructions` — renders it verbatim as a single
  block of text between `View state:` and `Highlights:`.
- Does not alter `[requires approval]` rendering based on which list
  (screen_actions vs tool_calls) the action appears in.

---

## What stays in consuming applications

The following are **not** part of the library and must never be imported by
library code:

| Concept | Owner | Reason |
|---------|-------|--------|
| `MessageRef`, `MessagingTargetProfile` | femtobot | Pydantic routing types specific to femtobot's transport layer. Renderer never uses them. |
| `AttentionSet`, attention model | femtobot | Runtime domain model; library has no concept of "attention". |
| SQLite resolvers, `DashboardRuntimeState` | femtobot | Persistence layer. Library is stateless. |
| `build_mail_screen()`, `build_communications_screen()` | femtobot | Business-logic builders for specific dashboard families. |
| `infer_dashboard_id()`, `build_attention_screen()` | femtobot | Routing and context assembly tied to femtobot session model. |
| `DashboardBoundaryDiagnostics` | femtobot | Runtime diagnostics for femtobot's execution boundary. |
| Extension action types | consumer | Application-specific fields on action references. See Decision 2. |

---

## Coupling decisions

### Decision 1: Remove messaging fields from `DashboardActionRef`

**Removed:** `message_ref: MessageRef | None` and
`messaging_target_profile: MessagingTargetProfile | None`.

**Rationale:** `render_screen()` does not access either field — confirmed by
static inspection of the renderer source. Both fields reference
`femtobot.contracts.messaging` Pydantic models that carry femtobot-specific
transport routing semantics. Keeping them in the library protocol would invert
the dependency: the library would depend on femtobot. This violates I-4.

**Replacement:** The `metadata: Mapping[str, Any] | None` field on
`DashboardActionRef` is an untyped pass-through for consumer-specific data
the renderer does not need to understand (I-5). Consumers that need typed
access to their own fields should use the extension pattern (Decision 2).

**Alternatives rejected:**

- *TypeVar / Generic `DashboardActionRef[M]`* — preserves type safety at the
  cost of making the core type parametric. Rejected because the renderer never
  accesses `M`; generic complexity buys nothing for a dump-engine type.
- *Copying `MessageRef` into the library* — deduplication illusion; the types
  would diverge and the library would still encode transport routing concepts
  it does not understand.

### Decision 2: Extension pattern for consumer-specific action fields

Consumers that need additional typed fields on action references define their
own dataclass and convert to `DashboardActionRef` at the rendering boundary.
The library neither knows nor enforces this pattern; it is implementation
guidance for consumers, not a library contract.

*Migration guidance for femtobot* (not a library contract):

```python
# femtobot/dashboards/femtobot_protocol.py
from agent_dashboard import DashboardActionRef

@dataclass(frozen=True)
class FemtobotActionRef:
    action_id: str
    label: str
    kind: str
    description: str | None = None
    target_source_id: str | None = None
    target_item_id: str | None = None
    target_display_name: str | None = None
    message_ref: MessageRef | None = None
    messaging_target_profile: MessagingTargetProfile | None = None

    def to_library(self) -> DashboardActionRef:
        return DashboardActionRef(
            action_id=self.action_id,
            label=self.label,
            kind=self.kind,
            description=self.description,
            target_source_id=self.target_source_id,
            target_item_id=self.target_item_id,
            target_display_name=self.target_display_name,
        )
```

Rationale for composition over subclassing: subclassing `frozen=True`
dataclasses in Python requires non-frozen subclasses or careful `__init__`
overrides. Composition makes the conversion boundary explicit and keeps the
extension type fully under consumer control.

### Decision 3: Two separate action lists (`screen_actions` and `tool_calls`)

`DashboardScreen` keeps two distinct lists rather than a single unified
`actions` list with a discriminator field.

**Rationale:** The semantic distinction is architecturally significant for all
consumers, not just femtobot. Screen actions are local and have no external
side effects. Tool calls are external, may be irreversible, and typically
route through an approval boundary. This difference matters at the structural
level because:

1. A consumer indexing action references by position or iterating both lists
   uniformly could accidentally treat a side-effecting tool call as a
   local-only screen action. Structural separation makes this impossible
   without explicit intent.
2. The distinction documents intent at the data model level, not just in
   comments or conventions.

**Important clarification:** The renderer renders both lists with identical
formatting (Invariant I-7). The structural distinction is consumer-side
semantic; the library itself does not enforce different behavior based on
which list an action reference appears in. This is intentional: enforcement
of the semantic distinction (e.g., routing tool calls through approval) is
the consuming application's responsibility.

**Alternatives rejected:**

- *Single `actions: tuple[DashboardActionRef, ...]` with `kind` discriminator*
  — loses the structural guarantee; a consumer iterating all actions cannot
  statically distinguish local from external at the type level.

### Decision 4: `view_state` typed as `Literal["collapsed", "expanded"]`

The original `view_state: str` is replaced with
`view_state: Literal["collapsed", "expanded"]`.

**Rationale:** An unconstrained string allows consumers to invent divergent
vocabulary (`"open"` vs `"expanded"`, `"hidden"` vs `"collapsed"`).
Constraining it at the library level establishes a shared two-state model.

**Semantics clarified:** `view_state` is an informational field (Invariant
I-6). The renderer prints it as-is; it does not alter what sections are
included in the output. Whether to show more or fewer items is the builder's
decision — it should be reflected in the `body_lines` and `highlights`
content it supplies, not in `view_state`. The field exists so the agent
reading the rendered output knows the current view state as context.

New states may be added in future minor versions. Removal of an existing
state is a breaking change.

**Alternatives rejected:**

- *Behavioral `view_state`* — renderer hides `body_lines` when
  `view_state="collapsed"`. Rejected because it inverts control: the builder
  would construct a full screen but the renderer would silently drop content.
  The renderer is a dump engine; content selection belongs in the builder.

### Decision 5: `body_lines` are plain text

`DashboardScreen.body_lines: tuple[str, ...]` are plain-text strings. The
library makes no provision for HTML, markdown, ANSI, or other formatting.

**Rationale:** The renderer concatenates lines and truncates by character
count. Character-position truncation is not safe if lines contain formatting
codes with variable display widths (e.g., ANSI escape sequences, markdown
emphasis). Consumers that want formatted output should apply formatting after
calling `render_screen()`, not before.

### Decision 6: `DashboardScreen.screen_instructions: str | None`

`DashboardScreen` gains an optional `screen_instructions` field rendered
between `View state:` and `Highlights:`.

**Rationale:** Screens are structurally self-describing (field names, action
labels, suggested_next_step per highlight) but not task-self-explaining. An
agent that has never seen a particular screen family does not know its
operating goal, recommended action sequence, or what to avoid. This is the
"affordance gap" — the screen shows what exists, not what to do.

`screen_instructions` provides a screen-level task framing written by the
builder. It is the first piece of text the agent reads after the header, so
it sets context before highlights and actions are processed.

**Why in the protocol, not in navigation_policy:** `navigation_policy` is
an assembly-layer concern in femtobot — it is dynamically generated and
injected into the prompt at session assembly time, outside the screen object.
`screen_instructions` is builder-owned data: the person building a screen
for a specific domain knows what the agent should do there. Putting it in the
screen object makes it portable — any consumer, any session assembly layer,
any rendering context gets it automatically.

**Design constraints:**
- Optional with default `None`. Builders are not required to provide it.
- Open string. The library does not constrain format or length.
- Rendered verbatim — subject to overall budget truncation, not truncated
  independently.
- Not a replacement for SKILL.md bootstrap skills. SKILL.md covers
  long-horizon agent behavior; `screen_instructions` covers the immediate
  operating context for the current screen visit.

**Alternatives rejected:**

- *Part of `body_lines`* — `body_lines` renders after highlights, so the
  agent reads action items before getting task context. Wrong ordering.
- *Part of `navigation_policy` (femtobot assembly layer)* — not portable
  across consumers; requires the assembly layer to know about every screen
  family's operating semantics.
- *New section header `Instructions:` in rendered output* — considered, but
  rendering as a plain block without header keeps the output clean for
  screens that need only a single orienting sentence.

### Decision 7: `DashboardActionRef.requires_approval: bool = False`

`DashboardActionRef` gains a `requires_approval` boolean field. When `True`,
the renderer appends `[requires approval]` to the action's rendered line.

**Rationale:** Without an explicit approval signal, an agent seeing
`tool_calls` must infer from `kind`, `description`, or external knowledge
whether an action is safe to emit without confirmation. This is the "kind
semantics opacity" risk — open-string `kind` values carry no universal
approval semantics, and `description` is optional and free-form.

`requires_approval` gives builders a single explicit boolean to declare
approval intent. It surfaces directly in the rendered output so the agent
has the signal at the point of decision, without needing to consult external
documentation or infer from field names.

**Semantics:** the flag is a rendering hint, not an enforcement point (I-9).
The library renders the marker; the consuming application gates execution.
This division is intentional — the library is a pure rendering layer.

**Convention guidance (not a library promise):** builders SHOULD set
`requires_approval=True` on all `tool_calls` that have external side effects
or affect third parties. `screen_actions` by definition have no external
effects and SHOULD use the default `False`. This is a convention; the
library does not validate it.

**Alternatives rejected:**

- *Derive from `kind` via a registered ontology* — closed kind ontology
  breaks extensibility; registries add complexity. The consuming application
  knows its own semantics better than the library does.
- *Separate `approval_required: bool` field* — identical to `requires_approval`
  with worse readability at construction time.
- *Encode approval in `description`* — free-form text; not machine-readable
  without parsing.

### Decision 8: Target fields are three named fields, not one

`DashboardActionRef` carries three distinct target fields:
`target_source_id: str | None`, `target_item_id: str | None`,
`target_display_name: str | None`.

**Rationale:** The renderer uses all three independently in its formatted
output: `[target={source_id}/{item_id}:{display_name}]`. Collapsing them into
a single `target_id: str | None` would lose the structural distinction between
source identity, item identity, and display name — information the consumer
needs to reconstruct round-trip targeting. The renderer's output format is the
ground truth here; field names follow what the renderer actually uses.

**Alternatives rejected:**

- *Single `target_id: str | None`* — was considered in an earlier design
  session but retracted after confirming the renderer uses three separate
  fields. A single field would require callers to pre-format the composite
  string, losing structured data.

---

## Non-promises

The library explicitly does not promise:

- Any awareness of LLM models, token counts, or context windows. `token_budget`
  is an approximate character hint; the library does not call any model API.
- Any persistence, state management, or session tracking.
- Any execution of actions. The library produces text; it does not dispatch
  `screen_actions` or `tool_calls`.
- Any opinion on how dashboards or screens are discovered, routed, or assembled.
  That is builder responsibility.
- Stability of `DashboardActionRef.metadata` semantics. It is an uninterpreted
  pass-through; the library promises only that it will not read or mutate it.
- Validated or constrained values for `severity`, `status`, or `kind`. These
  are open strings; the library does not validate them.
- Any behavioral difference between `view_state="collapsed"` and
  `view_state="expanded"` at render time.
- Enforcement of `requires_approval` semantics. The flag is a rendering hint;
  the library appends `[requires approval]` to the output but does not block
  or gate action execution.
- Interpretation or validation of `screen_instructions` content. It is
  rendered verbatim; correctness of the instructions is builder responsibility.
- A `navigation_policy` field or any per-screen dynamic policy injection.
  That concern belongs in the consuming application's session assembly layer
  (see M3 in `notes/screen-agent-ux.md`).

---

## Migration path (femtobot) — implementation guidance

*This section is guidance for femtobot's migration, not a library contract.*

1. Add `agent-dashboard` as a path dependency in femtobot's `pyproject.toml`.
2. Replace `from femtobot.dashboards.protocol import ...` with
   `from agent_dashboard import ...` in all dashboard modules.
3. Introduce `FemtobotActionRef` per Decision 2; update builders to produce
   it and convert via `.to_library()` before passing to `render_screen()`.
4. Update `view_state` field type annotations from `str` to
   `Literal["collapsed", "expanded"]`. No runtime behaviour changes.
5. Update field names: `target_source_id` and `target_item_id` were already
   correct in the original femtobot code; no rename needed there. Only the
   library-side proposal from session 1 that suggested `target_id` is
   retracted — the femtobot field names are preserved as-is.
6. Run mypy and the full test suite. Only import paths and type annotations
   change; no logic changes.

---

## Open questions (not blocking this proposal)

- Should `DashboardHighlight.severity` and `.status` be constrained
  `Literal`s, or remain open strings? Open strings allow consumers to define
  their own severity taxonomies; Literals would enforce a shared vocabulary.
  Defer to a follow-up ADR once a second consumer's needs are understood.
- Should `render_screen()` expose a truncation callback or post-render hook
  for consumers that need custom formatting? Low priority; consumers can wrap
  `render_screen()` themselves.
- Should the truncation marker string `"... [truncated]"` be a public
  constant? Consumers may need to detect or strip it. Low priority for now.
