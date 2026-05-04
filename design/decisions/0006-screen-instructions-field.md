# 0006 — screen_instructions: builder-owned task framing in the protocol

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (boundary.md Decision 6)
- **Supersedes:** —
- **Superseded by:** —

## Context

A `DashboardScreen` is structurally self-describing — field names, action
labels, and `suggested_next_step` per highlight convey what exists. But an
agent visiting a screen for the first time does not know its operating goal,
recommended action sequence, or what to avoid. The "affordance gap": the
screen shows what exists, not what to do.

Two existing mechanisms were evaluated as alternatives: `navigation_policy`
(femtobot's dynamic session-assembly injection) and `body_lines` (prepending
task context as plain text).

## Decision

`DashboardScreen.screen_instructions: str | None = None`.

Rendered verbatim between `View state:` and `Highlights:` — the first content
the agent reads after the header. The renderer does not parse, reformat, or
independently truncate it.

Semantics: open string, builder responsibility. The library renders whatever
it receives. Format, length, and correctness are the builder's concern.

## Alternatives considered

- **Prepend to `body_lines`** — `body_lines` renders after highlights, so the
  agent reads action items before getting task context. Wrong ordering.
- **`navigation_policy` in femtobot's session assembly layer** — not portable
  across consumers. Requires the assembly layer to know about every screen
  family's operating semantics. Any consumer that doesn't use femtobot's
  session model loses the feature entirely.
- **New section header `Instructions:` in rendered output** — considered, but
  rendering as a plain block without a header keeps output clean for screens
  that need only a single orienting sentence and avoids a structural marker
  that adds noise when absent.

## Consequences

- **Positive:** Portable — any consumer, any session assembly layer, any
  rendering context gets the instructions automatically because they live in
  the screen object.
- **Positive:** Builder-owned — the person building a screen for a specific
  domain encodes domain-appropriate task framing; no shared registry needed.
- **Negative:** Open string with no validation. Wrong or misleading
  instructions degrade agent behavior silently. The library cannot catch this.
- **Neutral:** Does not replace bootstrap SKILL.md. `screen_instructions`
  covers immediate per-screen context; SKILL.md covers long-horizon agent
  behavior. The two are complementary.

## Notes

`proposals/boundary.md` Decision 6. Invariant I-8.
