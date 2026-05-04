# 0007 — ScreenHub event model: full snapshot, not diff

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (hub-and-tui.md)
- **Supersedes:** —
- **Superseded by:** —

## Context

`ScreenHub` is the library's async reactive streaming component. Each event
it emits represents an update to the agent's visible screen state. The
fundamental question: should events be full `DashboardScreen` snapshots, or
diffs/deltas computed against the previous state?

This choice affects Hub complexity, consumer flexibility, and semantic clarity.

## Decision

Every event is a complete `DashboardScreen` snapshot. The Hub stores no
"previous state." Delta computation is consumer responsibility.

A subscriber that needs deltas compares two consecutive snapshots itself,
using `screen_diff()` from `agent_dashboard.testing` or its own logic.

## Alternatives considered

- **Structural diff events** — Hub computes and emits only what changed
  between consecutive screens. Rejected on three grounds: (1) diff semantics
  on a hierarchical object are ambiguous — replace? reorder? add?; (2) diff
  requires the Hub to store "previous" state, an additional stateful concern
  with no library-level benefit; (3) consumers disagree on what constitutes
  a meaningful delta (frontend WebSocket optimisation vs TUI rendering vs
  test assertions need different granularities).
- **Hybrid: snapshots with optional embedded diff** — adds both concerns to
  the library without eliminating the ambiguity. Rejected as complexity without
  payoff.

## Consequences

- **Positive:** Hub is stateless with respect to screen content; it only
  manages subscriber queues.
- **Positive:** Late subscribers, reconnecting consumers, and replaying
  subscribers always get a complete, valid screen — never a partial delta
  that requires prior state to be useful.
- **Positive:** `subscribe_from_latest()` solves the late-subscriber problem
  cleanly: the consumer gets the most recent complete snapshot immediately.
- **Negative:** Consumers that need only incremental updates receive full
  screens. For high-frequency publishing with large screens, this is
  more data per event than strictly necessary.
- **Neutral:** `screen_diff()` in `testing.py` provides a ready-made
  structural diff for consumers that want it without baking diff into the Hub.

## Notes

`proposals/hub-and-tui.md` § "Event model".
