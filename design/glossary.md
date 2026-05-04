# Glossary

Shared vocabulary for design discussions about `agent-dashboard`. When a
term in this glossary appears in a design doc, it means *this specific
thing*, not the generic English usage.

Terms are alphabetical within each section. Add new entries as they become
load-bearing in conversation; remove entries that fall out of use.

## Core concepts

- **Dashboard** — a named workspace view that groups related screens. Each
  dashboard has a `dashboard_id` (e.g. `"mail"`, `"communications"`). A
  dashboard is not rendered directly; rendering always targets a specific
  screen within it.

- **Screen** — the unit of rendering. A `DashboardScreen` is an immutable
  snapshot of what the agent "sees" at a given moment: a breadcrumb path,
  item count, body lines, highlights, and action references. Screens are
  value objects — they are not mutated, they are replaced.

- **Highlight** — a `DashboardHighlight` surfaces one notable item within a
  screen: a pending event, a risk, an opportunity. A highlight carries a
  severity, a status, a short summary, and an optional suggested next step.
  Highlights are not actions; they are observations.

- **Action reference** — a `DashboardActionRef` is a pointer to an action the
  agent *may* take from the current screen. It carries an `action_id` (opaque
  to the library), a human-readable `label`, a `kind`, and optional targeting
  metadata (`target_id`, `target_display_name`). The library never executes
  actions; it only renders them.

- **Screen action** — an action reference with local, state-only effect. No
  external side effects. Examples: marking a highlight explored, collapsing a
  section. Collected in `DashboardScreen.screen_actions`.

- **Tool call** — an action reference that triggers external execution and may
  have side effects. May require approval before execution. Collected in
  `DashboardScreen.tool_calls`. Semantically distinct from screen actions even
  though both use `DashboardActionRef` as the carrier type.

- **View state** — `"collapsed"` or `"expanded"`. Controls rendering density.
  `collapsed` surfaces highlights only; `expanded` includes full body lines.
  The renderer respects this field.

- **Body lines** — `DashboardScreen.body_lines: tuple[str, ...]`. Plain-text
  lines produced by the dashboard builder. The library treats them as opaque
  strings. Content type: plain text (no HTML, no markdown assumed).

- **Token budget** — the upper bound on rendered output size, passed as
  `token_budget: int` to `render_screen()`. The renderer truncates body lines
  to stay within budget. Budget is expressed in approximate character count
  (not tokens); callers supply it based on their model context constraints.

- **Builder** — consumer-side code that constructs `DashboardScreen` objects
  from domain data. Builders are not part of the library; they live in the
  consuming application (e.g. femtobot's `mail/dashboard.py`).

- **Extension type** — a consumer-defined subclass or wrapper of a library
  type that adds application-specific fields. Example: a femtobot
  `FemtobotActionRef` that extends `DashboardActionRef` with messaging routing
  fields. Extension types are not visible to the library's renderer.

## Boundary concepts

- **Library boundary** — the set of types and functions exported by
  `agent-dashboard`. Nothing outside this set is a library concern. See
  `proposals/boundary.md` for the definitive boundary specification.

- **Consumer** — any application that depends on `agent-dashboard`. Consumers
  construct screens, call `render_screen()`, and handle the rendered output.
  They are responsible for anything the library explicitly does not promise.

- **Coupling** — a dependency between library code and consumer-specific
  concepts. The library's design goal is zero coupling to any specific
  consumer. All consumer-specific fields belong in extension types, not in
  the library protocol.

## DX vocabulary

- **Guessability** — the property that a developer inventing a type or
  argument name by analogy lands on the actual API. High guessability reduces
  friction for new consumers.

- **Promise / non-promise** — a *promise* is a behavior the library guarantees
  across versions per SemVer; a *non-promise* is a behavior the library
  deliberately does not guarantee. Both should be stated explicitly.

## Process vocabulary

- **ADR** — Architecture Decision Record. A numbered, immutable record of a
  decision and its rationale. Lives in `decisions/`.

- **Proposal** — an in-flight recommendation, not yet decided. Lives in
  `proposals/`. Promoted to an ADR on acceptance.

- **Note** — exploratory thinking, scratch, research. Lives in `notes/`. Not
  load-bearing; can be deleted at any time.

- **Superseded** — an ADR whose decision has been replaced by a newer ADR.
  The old one is not deleted; its `Status` becomes `Superseded by NNNN` and
  the new one's `Supersedes` field points back.
