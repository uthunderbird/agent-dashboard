# 0005 — requires_approval is a rendering hint, not an enforcement point

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (boundary.md Decision 7)
- **Supersedes:** —
- **Superseded by:** —

## Context

An agent seeing `tool_calls` must know whether an action is safe to emit
without confirmation. The `kind` field is an open string with no universal
approval semantics. `description` is optional and free-form. Without an
explicit signal, the agent must infer from field names or external knowledge —
the "kind semantics opacity" risk.

The question was where enforcement of approval semantics should live: in the
library (gate execution) or in the consuming application.

## Decision

`DashboardActionRef.requires_approval: bool = False`.

When `True`, `render_screen()` appends `[requires approval]` to that action's
rendered line. The library renders the marker; it does not block, gate, or
otherwise act on the flag. Enforcement of approval semantics is the consuming
application's responsibility.

Convention (not a library promise): builders SHOULD set `requires_approval=True`
on all `tool_calls` with external side effects. `screen_actions` by definition
have no external effects and SHOULD use the default `False`.

## Alternatives considered

- **Derive approval from `kind` via a registered ontology** — closed kind
  ontology breaks extensibility; registries add complexity. The consuming
  application knows its own action semantics better than the library does.
- **Encode approval in `description`** — free-form text; not machine-readable
  without parsing; not a reliable signal for the agent.
- **Library enforces the flag** — the library is a pure rendering layer (ADR-0002);
  it has no execution model, no runtime, and no way to "enforce" anything.
  Enforcement at the rendering layer would require the library to either raise
  (impossible given P-5) or silently suppress output — both wrong.

## Consequences

- **Positive:** The agent has an explicit, unambiguous signal at the point of
  decision without consulting external documentation.
- **Positive:** The exact marker string `[requires approval]` is a stable
  promise (P-12); consumers can match against it if needed.
- **Negative:** The flag is advisory. A consumer that ignores it will silently
  execute side-effecting actions without approval. The library cannot prevent this.
- **Neutral:** Combined with the two-list structure (ADR-0004), consumers have
  both a structural and a per-action signal for approval routing.

## Notes

`proposals/boundary.md` Decision 7. Invariant I-9.
