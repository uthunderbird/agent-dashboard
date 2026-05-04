# Architecture Decision Records (ADRs)

Numbered, append-only records of accepted decisions. Once an ADR is
`Accepted`, it is immutable — to change a decision, write a new ADR that
supersedes the old one and update the old one's `Superseded by` field.

## Index

<!-- Add entries as ADRs are accepted. Keep newest at the top. -->

- [0013 — Testing kit: no pytest coupling](0013-testing-kit-no-pytest-coupling.md) — `hub_context()` async CM helper; no `pytest` import in library.
- [0012 — Custom serialization over dataclasses.asdict()](0012-serialization-module.md) — round-trip fidelity; tuple/list conversion; forward-compatible.
- [0011 — Persistence is consumer responsibility](0011-no-persistence-protocol.md) — no storage interfaces; `subscribe_from_latest()` for late subscribers.
- [0010 — live_tui is a standalone function](0010-live-tui-standalone-function.md) — TUI does not depend on Hub; lazy `rich` import.
- [0009 — group_id annotation on ScreenHub events](0009-screenhub-group-id.md) — neutral vocabulary for turn/batch/request grouping.
- [0008 — ScreenHub.publish() uses call_soon_threadsafe](0008-screenhub-thread-safe-publish.md) — not run_in_executor; microsecond-scale operation.
- [0007 — ScreenHub event model: full snapshot](0007-screenhub-snapshot-model.md) — no diffs in Hub; delta computation is consumer responsibility.
- [0006 — screen_instructions: builder-owned task framing](0006-screen-instructions-field.md) — rendered verbatim between View state and Highlights.
- [0005 — requires_approval is a rendering hint](0005-requires-approval-flag.md) — not an enforcement point; library appends marker, consumer gates execution.
- [0004 — Two separate action lists](0004-two-action-lists.md) — `screen_actions` (local) and `tool_calls` (external); structural distinction.
- [0003 — DashboardActionRef extension pattern](0003-action-ref-extension-pattern.md) — consumer-owned dataclass + `.to_library()` conversion; `metadata` as escape hatch.
- [0002 — Renderer is a pure, dump-engine function](0002-renderer-as-pure-function.md) — no behavioral decisions; content selection is builder responsibility.
- [0001 — Library boundary](0001-library-boundary.md) — what enters agent-dashboard; one-way dependency; zero runtime deps.

## Adding an ADR

1. Copy `0000-template.md` to `NNNN-kebab-case-title.md` using the next
   monotonic number.
2. Fill in Context, Decision, Alternatives, Consequences. Alternatives are
   mandatory.
3. Open as `Status: Proposed`. Flip to `Accepted` when the call is made.
4. Add an entry to the Index above.

## Why ADRs

Decisions decay without context. Six months from now, "why did we exclude
messaging fields from DashboardActionRef?" should have a one-link answer,
not a git-archaeology session.
