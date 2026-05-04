# Proposals (RFCs in flight)

Drafts being debated. Not yet decided.

A proposal is a document that:
- describes a concrete change or addition,
- has a recommendation (not just a survey of options),
- can plausibly become an ADR.

## Lifecycle

```
notes/  ─┐
         ├─▶  proposals/<title>.md  ─▶  decisions/NNNN-<title>.md
external ┘                              (proposal then archived/deleted)
```

When a proposal is accepted: distill its decision and rationale into an
ADR under `decisions/`, and either delete the proposal or move its
exploratory content to `notes/`. The proposal folder should not become a
graveyard of "decided but never archived" docs.

## Index

<!-- Keep this list small. If it grows past ~5, something is stalling. -->

- [Library boundary specification](boundary.md) — what enters `agent-dashboard`,
  what stays in consuming applications, coupling decisions with rejected
  alternatives, library invariants, and renderer semantics. Proposed 2026-04-26.
- [External developer API](external-dev-api.md) — public surface, promises,
  non-promises, golden path, error surface, DX rubric (R-1–R-10), and builder
  pattern. Proposed 2026-04-26.

## Frontmatter

```yaml
---
title: <human-readable title>
status: draft | proposed
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```
