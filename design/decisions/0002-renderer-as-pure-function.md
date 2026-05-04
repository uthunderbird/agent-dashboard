# 0002 — Renderer is a pure, dump-engine function

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (boundary.md)
- **Supersedes:** —
- **Superseded by:** —

## Context

The renderer must turn a `DashboardScreen` into a string for inclusion in an
LLM prompt. Two design axes needed resolution: (1) should the renderer make
behavioral decisions based on field values (e.g. hide body_lines when
`view_state="collapsed"`), or should it render whatever it receives? (2) should
it be a method, a class, or a free function?

## Decision

`render_screen(screen, *, token_budget=4000) -> str` is a pure free function:

- No I/O, no side effects, no global state.
- Same `(screen, token_budget)` → same output, always.
- Does not alter what sections it renders based on `view_state`.
- Does not interpret or validate open-string fields (`severity`, `status`,
  `kind`).
- Does not read or render `DashboardActionRef.metadata`.
- Renders `screen_actions` and `tool_calls` with identical formatting.
- Never raises for any valid Python input.

Content decisions (what to put in `body_lines`, which highlights to include,
whether to expand or collapse a view) are the builder's responsibility,
expressed in the `DashboardScreen` they construct.

## Alternatives considered

- **Behavioral `view_state`** — renderer hides `body_lines` when
  `view_state="collapsed"`. Rejected: inverts control. A builder that constructs
  a full screen would silently lose content at render time. The renderer is a
  dump engine; content selection belongs in the builder.
- **Renderer class with configurable output strategy** — allows per-instance
  customization (e.g. different truncation strategies). Rejected: adds
  complexity without evidence of need; a pure function is trivially testable
  and composable.
- **Renderer that validates field semantics** — raises on unknown `severity`
  values, mismatched `item_count`, etc. Rejected: open-string policy and
  dump-engine role are incompatible with semantic validation. Callers validate
  at their own boundaries.

## Consequences

- **Positive:** Deterministic truncation — tests can assert exact output for
  any `(screen, token_budget)` pair.
- **Positive:** Zero asyncio overhead on import; the base package is
  synchronous and has no event-loop entanglement.
- **Positive:** Trivial to test; no mocking required.
- **Negative:** Consumers cannot get different rendering behavior from the same
  screen without building a different screen. This is intentional, but
  occasionally inconvenient.
- **Neutral:** `view_state` becomes purely informational — the agent reads it
  as context but the renderer does not act on it.

## Notes

Truncation algorithm detail: `char_budget = max(32, token_budget * 4)`.
Full renderer semantics: `proposals/boundary.md` § "Renderer semantics".

Empty-collection behaviour: `highlights=()`, `screen_actions=()`, and
`tool_calls=()` all omit their section headers entirely — consistent
dump-engine behaviour. An earlier version of `external-dev-api.md` incorrectly
stated `highlights=()` renders `Highlights: none`; that doc has been corrected.

`dashboard_id` and `screen_id` are routing identifiers used by consumers;
they are not part of the rendered output. `DashboardHighlight.source_ref` is
a consumer back-reference; it is not rendered.
