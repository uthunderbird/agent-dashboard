# 0004 — Two separate action lists: screen_actions and tool_calls

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (boundary.md Decision 3)
- **Supersedes:** —
- **Superseded by:** —

## Context

Actions available on a screen fall into two categories with meaningfully
different semantics: local actions with no external side effects ("snooze",
"dismiss", "navigate") and external actions that may be irreversible or
affect third parties ("reply", "complete task", "send message"). The question
was whether to separate these structurally or use a single list with a
discriminator field.

## Decision

`DashboardScreen` carries two distinct action lists:
- `screen_actions: tuple[DashboardActionRef, ...]` — local, side-effect-free.
- `tool_calls: tuple[DashboardActionRef, ...]` — external, may require
  approval before execution.

The renderer formats both lists with identical logic (rendering symmetry —
see ADR-0002). The structural distinction is consumer-enforced, not
library-enforced.

## Alternatives considered

- **Single `actions: tuple[DashboardActionRef, ...]` with `kind` discriminator**
  — loses the structural guarantee. A consumer iterating all actions cannot
  statically distinguish local from external at the type level; it must parse
  or match `kind` strings. Open-string `kind` carries no universal approval
  semantics.

## Consequences

- **Positive:** At the type level, iterating `tool_calls` gives only
  side-effecting actions; mixing is impossible without explicit intent.
- **Positive:** The distinction documents architectural intent in the data
  model, not just in comments or conventions.
- **Positive:** Approval routing in the consuming application can key on
  the list, not on parsing `kind` values.
- **Negative:** Two empty tuples instead of one in the common case where a
  screen has no actions of one type. Minor verbosity.
- **Neutral:** Renderer rendering symmetry (ADR-0002) means the visual output
  does not reflect the distinction — the agent sees both sections formatted
  identically. The builder uses `requires_approval=True` (ADR-0005) to
  signal approval intent within the rendered output.

## Notes

`proposals/boundary.md` Decision 3.

The renderer outputs `Screen actions:` before `Tool calls:` — local/informational
actions appear before external/approval-requiring ones. This ordering is
intentional: the agent reads local options first, then external ones. A test
asserting this order exists in `tests/test_renderer.py`
(`test_both_action_lists_populated_order_and_isolation`).
