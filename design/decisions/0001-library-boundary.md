# 0001 — Library boundary: what enters agent-dashboard

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (boundary.md, two rounds)
- **Supersedes:** —
- **Superseded by:** —

## Context

`agent-dashboard` is extracted from femtobot's `dashboards/` module. Three
forces shaped where the boundary had to be drawn:

1. **Divergent release cycles.** femtobot and a second consuming application
   have independent release schedules. Mixing femtobot-specific types into a
   shared rendering library would couple version bumps across two codebases
   with no common owner.

2. **Dependency footprint.** femtobot carries Pydantic, a Telegram client, and
   a full asyncio runtime stack. A second consumer — or any future consumer —
   cannot be required to install femtobot just to use three dataclasses and a
   pure renderer.

3. **Semantic neutrality.** `DashboardActionRef` with `message_ref: MessageRef`
   encodes femtobot's transport routing semantics in a type that must be shared.
   A second consumer would inherit concepts it has no use for. Shared vocabulary
   must be neutral across consumers.

The original code mixed both concerns freely because femtobot was the only
consumer. The arrival of a second consumer made that mixture untenable.

## Decision

No module enters the library without an accepted ADR. The one-way dependency
rule — consumer imports from library; library never imports from consumer —
applies to every module unconditionally, regardless of whether it is in the
base package or an optional extra.

The base package (`protocol.py`, `renderer.py`, `__init__.py`) exports exactly
four names: `DashboardHighlight`, `DashboardActionRef`, `DashboardScreen`,
`render_screen`. Optional modules (`hub`, `tui`, `testing`, `serialization`,
`actions`) are governed by their own ADRs; they extend the library without
changing this base boundary.

## Alternatives considered

- **Keep types in femtobot; second consumer installs femtobot as a dependency**
  — would require the second consumer to take on femtobot's full dependency
  graph (Pydantic, Telegram client, asyncio stack) for three dataclasses and
  one function. Rejected: femtobot is not a utility library; its dependency
  footprint is incompatible with lightweight consumer use cases.

- **Keep femtobot types in the library and mark them optional** — would require
  the library to carry Pydantic as a dependency and encode femtobot's transport
  routing concepts. Rejected: violates one-way dependency; second consumer
  would inherit femtobot semantics.

- **Single generic consumer-extension point (TypeVar/Protocol)** — avoids
  hard-coding femtobot types at the cost of making the core type parametric.
  Rejected: the renderer never accesses extension data; generic complexity buys
  nothing for a dump-engine type.

- **Extract only the renderer, leave protocol in femtobot** — half-extraction;
  the second consumer would still need femtobot as a dependency to get the data
  types. Rejected: protocol and renderer must travel together.

## Consequences

- **Positive:** Zero runtime dependencies in the base package. Any consumer
  installs `agent-dashboard` without pulling in Pydantic, a Telegram client,
  or any femtobot infrastructure.
- **Positive:** Library invariants are testable in isolation. No mock of
  femtobot internals required; tests run on the library alone.
- **Positive:** The ADR-gated admission rule is a documented convention: each
  new module requires an accepted ADR. This is not enforced by CI today; it
  is enforced by review. The value is that boundary violations require
  overriding a written decision, not just adding a file.
- **Negative:** femtobot has 39 `DashboardActionRef` construction sites across
  three files. Migration requires auditing each site. Most pass only the
  library-compatible fields (`action_id`, `label`, `kind`, targets), so
  per-site changes are small; but the audit surface is real.
- **Negative:** If femtobot introduces `FemtobotActionRef` with a
  `.to_library()` conversion (see ADR-0003), that conversion must be updated
  whenever `DashboardActionRef` gains new fields in the library. This is an
  ongoing maintenance coupling, not a one-time migration cost.
- **Neutral:** `metadata: Mapping[str, Any] | None` on `DashboardActionRef`
  is an untyped escape hatch for consumer-specific data the renderer ignores.
  Consumers that need typed access define their own extension dataclass (ADR-0003).
- **Neutral:** `DashboardActionRef` is `frozen=True` but hashability is
  conditional: passing a mutable `dict` as `metadata` causes `hash()` to
  raise `TypeError` at runtime. Python does not enforce tuple annotations —
  passing a `list` to collection fields also breaks hashability silently.
  These are caller-side invariants; the library does not validate them.

## Notes

Full coupling decisions with rejected alternatives: `proposals/boundary.md`.
femtobot construction sites: `runtime/session/context.py`,
`dashboards/mail/dashboard.py`, `dashboards/communications/dashboard.py`.
