# agent-dashboard — design docs

This directory holds living design documentation for `agent-dashboard`. It is
the canonical place for any document that influences how the library evolves,
how it should feel to use, or what was decided and why.

## Layout

| File / Folder | Purpose | Lifetime |
|---------------|---------|----------|
| `VISION.md` | **SSOT.** Functional vision of the library — the problem it solves and what using it feels like. Updated in place. | Living (versioned) |
| `glossary.md` | Shared vocabulary used across the docs in this directory. | Living |
| `decisions/` | Accepted Architecture Decision Records (ADRs). Append-only history of what was decided and why. | Permanent |
| `proposals/` | RFCs in flight — drafts being debated, not yet accepted. When accepted, distilled into an ADR and the proposal is archived or deleted. | Transient |
| `dx/` | Developer Experience design docs targeting **human** users of the library. | Living |
| `agent-dx/` | Agent-DX design docs targeting **LLM agents** as users (introspection, error legibility, schema clarity). | Living |
| `notes/` | Exploratory thinking, scratch work, research dumps. Not yet shaped into a proposal. | Transient |

When introducing a term that appears repeatedly in design discussions,
add it to `glossary.md` so future readers and agents share precise vocabulary.

## How to add a doc

- **Decision?** Copy `decisions/0000-template.md`, give it the next number,
  write it. ADRs are immutable once `Status: Accepted`; supersede with a
  newer ADR rather than editing.
- **Proposal?** Drop a kebab-case `.md` into `proposals/`. No number. When
  accepted, promote to an ADR.
- **DX or agent-DX deep dive?** Add a kebab-case `.md` to the appropriate
  folder and link it from that folder's `README.md`.
- **Just thinking out loud?** Use `notes/`. Move to `proposals/` when it
  firms up.

## Doc states

Every doc that isn't an ADR should carry a frontmatter block:

```yaml
---
title: <human-readable title>
status: draft | proposed | accepted | superseded | archived
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

ADRs use the same field names but `status` is constrained to: `Proposed`,
`Accepted`, `Rejected`, `Superseded by NNNN`, `Deprecated`.
