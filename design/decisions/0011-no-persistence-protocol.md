# 0011 — Persistence is consumer responsibility; library provides no protocol

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (persistence.md session)
- **Supersedes:** —
- **Superseded by:** —

## Context

Should the library define a persistence protocol — interfaces for storing,
retrieving, and replaying `DashboardScreen` snapshots? Two consumers exist:
femtobot (reconstructs screens from event log replay; does not store screens
directly) and a corporate project (unknown persistence model). A third
consideration: eval harnesses need reproducible screen sequences.

## Decision

The library provides no persistence protocol, no storage interfaces, and no
replay mechanism. `subscribe_from_latest()` on `ScreenHub` is the only
accommodation for late subscribers — it yields the most recent snapshot
immediately, before streaming subsequent events.

Consumers implement persistence in their own layer. `screen_to_dict()` and
`screen_from_dict()` in `agent_dashboard.serialization` (ADR-0012) provide
the serialization primitive they need.

## Alternatives considered

- **Abstract persistence protocol (`ScreenStore` interface)** — defines
  `save(screen)` / `load(screen_id)` / `replay(group_id)`. Rejected: femtobot
  already has an event-sourced reconstruction model that doesn't map to a
  screen-store abstraction. A second consumer with a different model would
  either not implement the interface or implement it incorrectly. No useful
  unification exists.
- **Optional ring-buffer log in ScreenHub** — Hub accumulates the last N
  screens; late subscribers can replay them. Deferred to v2: requires an
  explicit consumer requirement to justify the added state and API surface.
  Marked in ROADMAP.md under "Deferred (v2)".
- **`PickleStore` or `JSONStore` built-in implementations** — would pick a
  specific storage technology, locking the library to it. Rejected.

## Consequences

- **Positive:** Library remains stateless (except for in-flight subscriber
  queues in ScreenHub). No storage dependencies.
- **Positive:** Consumers with incompatible persistence needs are not
  constrained by a shared interface.
- **Negative:** Each consumer re-implements a storage adapter. The
  serialization module (ADR-0012) reduces but does not eliminate this cost.
- **Neutral:** The v2 ring-buffer log for ScreenHub replay is deferred, not
  rejected. It may be added when a concrete consumer requirement justifies it.

## Notes

ROADMAP.md § "Explicit non-goals" and § "Deferred (v2)".
