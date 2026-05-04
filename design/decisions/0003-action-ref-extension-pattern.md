# 0003 — DashboardActionRef extension pattern for consumer-specific fields

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (boundary.md Decisions 1 & 2)
- **Supersedes:** —
- **Superseded by:** —

## Context

The original femtobot `DashboardActionRef` carried two femtobot-specific
fields: `message_ref: MessageRef | None` and
`messaging_target_profile: MessagingTargetProfile | None`. These referenced
Pydantic models in femtobot's transport layer. The renderer never accessed
either field (confirmed by static inspection).

ADR-0001 established that the library must not import from any consuming
application. Keeping these fields in the shared type would invert the
dependency: the library would depend on femtobot's Pydantic stack.

The question this ADR answers: given that consumer-specific fields are
excluded, how should a consumer that needs additional typed fields attach
them?

`DashboardActionRef` already provides `metadata: Mapping[str, Any] | None`
as a renderer-opaque untyped pass-through for lightweight use cases. This
ADR covers the typed extension case.

## Decision

Consumers that need additional typed fields on action references define their
own dataclass and convert to `DashboardActionRef` at the rendering boundary.
The library provides no mechanism for this — it is a consumer-side convention.

```python
# In the consuming application — not in the library
from dataclasses import dataclass
from agent_dashboard import DashboardActionRef
from femtobot.contracts.messaging import MessageRef, MessagingTargetProfile

@dataclass(frozen=True)
class FemtobotActionRef:
    # Mirror all DashboardActionRef fields
    action_id: str
    label: str
    kind: str
    description: str | None = None
    target_source_id: str | None = None
    target_item_id: str | None = None
    target_display_name: str | None = None
    requires_approval: bool = False
    metadata: None = None  # unused in femtobot; typed narrowly
    # Consumer-specific fields
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
            requires_approval=self.requires_approval,
        )
```

Consumers that do not need typed extension fields may construct
`DashboardActionRef` directly — the `.to_library()` pattern is not mandatory.

## Alternatives considered

- **Generic `DashboardActionRef[M]` with TypeVar** — preserves type safety
  for the consumer's extra data at the cost of making the core type
  parametric. Rejected: the renderer never accesses `M`; generic complexity
  buys nothing for a dump-engine type.

- **Copy `MessageRef` into the library** — deduplication illusion; the two
  copies would diverge and the library would still encode transport concepts
  it does not understand. Rejected.

- **Subclassing `DashboardActionRef`** — `@dataclass(frozen=True)` subclasses
  of `frozen=True` parents compile in Python, but carry a field-ordering
  constraint: new fields added in the subclass cannot be required (no default)
  if the parent already has optional fields (with defaults). Since
  `DashboardActionRef` has six optional fields after the three required ones,
  a subclass can only add optional fields. More importantly, the subclass
  becomes a subtype of `DashboardActionRef` — any renderer or consumer code
  that accepts `DashboardActionRef` will accept the subclass, silently
  carrying consumer-specific fields through library code. The explicit
  composition boundary is clearer and keeps the extension type fully under
  consumer control. Rejected.

## Consequences

- **Positive:** Library stays dependency-free; no Pydantic, no femtobot types.
- **Positive:** Each consumer controls its own extension type independently.
  Two consumers with incompatible extra fields need no coordination.
- **Positive:** The conversion boundary is explicit and testable. Consumer
  tests can assert that `.to_library()` produces the expected `DashboardActionRef`
  without touching library internals.
- **Negative:** femtobot has approximately 39 `DashboardActionRef` construction
  sites across three files (`runtime/session/context.py`,
  `dashboards/mail/dashboard.py`, `dashboards/communications/dashboard.py`).
  Most pass only library-compatible fields, so per-site changes are small —
  but the audit surface is real.
- **Negative:** When `DashboardActionRef` gains new optional fields in future
  library releases, consumers using the `.to_library()` pattern must decide
  whether to thread those fields through their extension type. This is an
  ongoing maintenance coupling proportional to how frequently the library
  adds fields.
- **Neutral:** `metadata: Mapping[str, Any] | None` on `DashboardActionRef`
  covers the lightweight case — consumer-specific data that does not need
  typed access at the library boundary. The `.to_library()` pattern covers
  the typed case. Both are valid; choice depends on whether the consumer
  needs typed access to the extra fields in its own code.
- **Neutral:** Consumers that pass consumer-specific objects as `metadata`
  should be aware that hashability of the resulting `DashboardActionRef`
  depends on whether `metadata` is hashable (see ADR-0001).

## Notes

`proposals/boundary.md` Decisions 1 and 2 have the full rationale and the
original femtobot migration context.

For the common pattern of constructing many `DashboardActionRef` instances
with repeated fields (e.g. 25+ similar actions in femtobot), the planned
`ActionSpec` helper in `agent_dashboard.actions` (see ROADMAP.md, item I6)
provides a library-side alternative to manual repetition — a typed named
constant with a `.for_target()` method. That is a separate ADR.
