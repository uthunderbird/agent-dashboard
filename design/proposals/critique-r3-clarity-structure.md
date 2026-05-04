---
title: "VISION.md — Round 3 critique: clarity, structure, and readability"
version: 1
date: 2026-04-26
status: active
target: design/VISION.md (version 3)
focus: Clarity, structure, and readability for a Python developer unfamiliar with femtobot
---

# VISION.md — Round 3 critique: clarity, structure, and readability

## Scope

This critique evaluates VISION.md version 3 from the standpoint of a Python
developer who has never used femtobot, is building an LLM agent application,
and wants to understand whether `agent-dashboard` is relevant to them.

Findings in this round are distinct from rounds 1 and 2:
- Round 1 addressed data/policy framing, action_id scope, and portability overclaims.
- Round 2 addressed DX consistency, rendering order accuracy, and femtobot vocabulary.
- Round 3 addresses first-reader orientation, undefined vocabulary, structural weight,
  and gaps in the newcomer reading experience.

Evidence boundary: document text only.

---

## Critical Findings

### C1. "Screen" is used as a defined term before it is defined

`verified issue`

The word "screen" appears nine or more times in the document before any
definition is offered. "Screen families," `screen_instructions`,
`DashboardScreen`, and "screen-level" are all deployed as established
vocabulary before the reader knows what a screen is in this library's terms.

A developer unfamiliar with this pattern cannot form a stable mental model.
The implicit definition — something like "a structured snapshot of an agent's
workspace at one point in time, rendered as plain text for inclusion in an LLM
prompt" — never appears as a sentence anywhere in the document. The reader
must reconstruct it from accumulated context.

This is not a minor omission. "Screen" is the central noun of the library.
Without a grounded definition, the problem section, the DX section, and the
design constraints section all have an undefined term at their center.

### C2. Meta-opening delays orientation

`verified issue`

The first paragraph of the document (four sentences) is governance
housekeeping:
- SSOT declaration
- conflict resolution rule ("When this document and a proposal conflict, update one of them")
- update discipline ("Update this document in place")
- changelog reference

This content is useful for maintainers and contributors. It is not useful for
a developer who has just arrived and does not yet know what the library does.
The problem section — the first content-bearing section — is separated from
the title by four sentences of editorial policy and a horizontal rule. The
word "LLM" does not appear until the second section.

A newcomer must absorb maintenance protocol before the library's purpose is
stated. This inverts the expected reading priority.

### C3. "Bootstrap skills" is unexplained jargon

`verified issue`

The non-responsibilities bullet reads:

> Bootstrap skills. Detailed operating instructions for complex screen
> families belong in your agent framework's bootstrap or system-prompt
> configuration — not in `screen_instructions`, which is for immediate
> per-turn context, and not in this library, which has no bootstrap concept.

A reader unfamiliar with agent framework conventions does not know what
"bootstrap" means in this context. The bullet does not define it. The embedded
phrase "per-turn context" further assumes familiarity with how LLM conversation
turns are structured. The concept of "complex screen families" is also
undefined — the reader does not know what makes a screen family "complex" or
what the spectrum looks like.

This is the only non-responsibility bullet that requires external vocabulary to
parse. A first-time reader cannot evaluate whether this exclusion is relevant
to them.

---

## Lower-Priority Findings

### L1. Document structurally weighted toward non-responsibilities

`bounded concern`

"What the library does not do" contains six items and rivals "What agent-
dashboard provides" in prose volume. For a reader forming a first impression,
this inverts the expected ratio: a library should be defined primarily by what
it does. The section is not wrong, but its structural weight creates a document
whose center of gravity is defensive. The signal a reader receives is: "this
library is aware of many things it might be asked to do and declines all of
them."

### L2. Target audience is never stated

`bounded concern`

The document does not say who it is for. The "multi-consumer divergence"
problem bullet implies multiple teams building shared infrastructure. The DX
section describes a solo developer experience. A reader cannot resolve whether
`agent-dashboard` is a building block for individual projects or a shared
infrastructure library for organizations. This affects the core evaluation
question ("is this for me?") and is never answered.

### L3. The DX "golden path" claim is promissory rather than demonstrative

`bounded concern`

The DX section closes with: "The golden path — from zero to a rendered screen
— should take fifteen lines of code and no documentation beyond the type
signatures."

This is a design aspiration, not evidence. No example, sketch, or abbreviated
type signature appears anywhere in the document. The DX section describes what
a developer will do (construct, render, instruct, signal, extend), but provides
no artifact — not even a four-line pseudocode example — that would let the
reader form an independent judgment. The claim cannot be verified from the
document alone.

### L4. "View state" is used without definition in the rendering order

`bounded concern`

DX bullet 3 describes the rendering order as:
"View state → `screen_instructions` → Highlights → Actions"

"View state" appears only in this one sentence. It is not defined. A reader
does not know what it corresponds to in the data model: is it a dedicated
field, a computed section derived from other fields, or a label for the
`DashboardScreen` contents minus highlights and actions? The term does not
appear in the three-dataclass description in "What agent-dashboard provides."

### L5. "Relationship to other documents" placed too late

`bounded concern`

This section appears fifth out of six content sections — after Design
constraints, which is the most technical section in the document. For a
developer deciding whether to go deeper, the document map is most useful
early, before or immediately after the library description. Placed last, it
reads like an appendix rather than a navigation aid for someone building an
orientation.

### L6. "No consumer imports" constraint name is ambiguous

`working criticism`

The constraint is named with one phrase and stated in one sentence: "The
library must not import anything from a consuming application. The dependency
graph is one-directional: consumer → library."

The phrase "No consumer imports" can be misread as "the library itself makes
no imports" (a different, incorrect claim) rather than "the library does not
depend on consumer code." The constraint is a meaningful portability and
encapsulation property, but the name does not convey it naturally to a first
reader, and the single-sentence statement provides no elaboration.

---

## Recommendations

**R1.** Move or demote the governance paragraph (SSOT declaration, conflict
resolution rule, update discipline) so the problem statement opens the
document. Governance text can live after the library description, in a footer,
or as a collapsible block.

**R2.** Insert a one-sentence definition of "screen" at or near its first use.
Candidate: "A screen is a structured snapshot of an agent's workspace at one
point in time, rendered as plain text for inclusion in an LLM prompt."

**R3.** State target audience in one sentence near the top. Candidate: "This
library is for Python developers building LLM agent applications where multiple
screen types need consistent, token-bounded prompt formatting."

**R4.** Rewrite or ground the "Bootstrap skills" non-responsibility bullet
using only vocabulary the document has already established. If "bootstrap" is
essential, define it inline. If it is not essential, merge its content with
`screen_instructions` scope.

**R5.** Add a pseudocode sketch (4–8 lines) to the DX section to make the
"fifteen lines" claim concrete and let the reader form an independent
evaluation.

**R6.** Move "Relationship to other documents" to immediately after "What
agent-dashboard provides," before the DX section.

**R7.** Add one clause to "No consumer imports" clarifying the direction of the
claim: that the library does not depend on consumer code, making it safe to use
across any consuming application without coupling risk.

**R8.** Define "View state" at its only appearance in the rendering-order
description. Even a parenthetical is enough: "(the screen's core workspace
data — pending items, notable events, available actions)".

---

## Compact Ledger

| Field | Content |
|-------|---------|
| **Target document** | `design/VISION.md` (version 3) |
| **Focus** | Clarity, structure, and readability for a developer unfamiliar with femtobot |
| **Critical findings** | C1 "screen" undefined before use; C2 meta-opening delays orientation; C3 "bootstrap skills" is unexplained jargon |
| **Lower-priority findings** | L1 document weighted toward non-responsibilities; L2 target audience unstated; L3 golden-path claim promissory; L4 "View state" undefined; L5 document map placed too late; L6 "No consumer imports" name ambiguous |
| **Ordered fix list** | 1. Move governance paragraph so problem statement opens the document. 2. Insert one-sentence definition of "screen" at first use. 3. State target audience in one sentence near the top. 4. Rewrite "Bootstrap skills" bullet without external jargon. 5. Add pseudocode sketch (4–8 lines) to DX section. 6. Move "Relationship to other documents" earlier (after library description). 7. Add one-clause clarification to "No consumer imports." 8. Define "View state" inline at its appearance in rendering-order description. |
