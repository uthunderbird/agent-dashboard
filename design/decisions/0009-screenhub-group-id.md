# 0009 — group_id annotation on ScreenHub events

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (hub-and-tui.md)
- **Supersedes:** —
- **Superseded by:** —

## Context

Different consuming applications partition their work differently: femtobot
uses "turns" (one agent reasoning cycle), a corporate consumer uses "batches"
or "requests". Subscribers downstream of a Hub — frontends, TUI, eval
harnesses — often need to know which group of screens belongs together.

The question was whether to add a grouping annotation to events, and if so,
what vocabulary to use.

## Decision

`publish(screen, *, group_id: str | None = None)`.
Subscribers receive `tuple[DashboardScreen, str | None]` — the screen and
its group tag.

`group_id=None` means "no group". The library assigns no meaning to the
string value; it is consumer vocabulary passed through opaquely.

The field is named `group_id`, not `turn_id` or `batch_id`.

## Alternatives considered

- **`turn_id`** — femtobot-specific vocabulary. A corporate consumer that
  processes "requests" or "jobs" would use the field but the name would be
  misleading. Rejected: the library serves multiple consumers with different
  execution models.
- **No grouping annotation** — consumers that need grouping would add their
  own wrapper layer. Rejected: grouping is a sufficiently common concern
  (eval harnesses, TUI history, WebSocket multiplexing) that omitting it
  forces every consumer to reinvent the same wrapper.
- **Structural `Group` type wrapping the event** — `tuple[DashboardScreen, str | None]`
  plus an envelope. Rejected: over-engineering for an opaque string. If
  richer group metadata becomes necessary, a future ADR can introduce a
  proper type.

## Consequences

- **Positive:** femtobot maps `turn_count → group_id`; corporate consumer maps
  its own unit. Neither is forced into the other's vocabulary.
- **Positive:** Eval harnesses can assert that all screens for a given turn
  were received in order by filtering on `group_id`.
- **Neutral:** `group_id` is the library's only concession to consumer
  execution models; the Hub itself has no concept of turns, batches, or
  sessions.

## Notes

`proposals/hub-and-tui.md` § "group_id semantics".
