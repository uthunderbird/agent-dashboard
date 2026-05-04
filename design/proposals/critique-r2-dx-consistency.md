---
title: Round 2 critique — DX consistency and completeness
target: VISION.md (version 2)
round: 2 of 3
focus: Internal consistency of DX vision and completeness; contradictions between sections; layer misattribution
date: 2026-04-26
status: active
---

# Round 2 critique — DX consistency and completeness

## Scope

This critique covers only findings distinct from Round 1 (problem framing accuracy).
Round 1 findings are in `critique-r1-problem-framing.md`.

All findings are derived from VISION.md version 2 as of 2026-04-26,
cross-checked against the confirmed public surface:
DashboardHighlight, DashboardActionRef, DashboardScreen (frozen dataclasses),
render_screen() (pure function), token_budget parameter,
char_budget = max(32, token_budget * 4), truncation with "... [truncated]".

---

## Critical findings

### C1 — `token_budget` and truncation are absent from the DX section

**Classification:** verified issue

The DX section describes `render_screen()` as "a single function call" with
no mention of its only required non-default parameter (`token_budget`) or its
principal behavioral consequence (character-budget truncation with a
"... [truncated]" marker).

`token_budget` is not an implementation detail — it is the mechanism that
determines what the LLM actually receives. A developer who passes a small
value without understanding the `max(32, token_budget * 4)` character ceiling
will receive silently truncated output. The golden-path promise ("fifteen
lines of code and no documentation beyond the type signatures") is false for
any developer who needs to size their budget correctly, because the budget
semantics are approximated (4× char multiplier) in a non-obvious way.

The DX section should name `token_budget`, state that the output is
character-bounded (not tokenizer-bounded), and note the truncation marker so
developers can detect or handle truncated output.

---

### C2 — `screen_instructions` placement implied incorrectly in DX bullet 3

**Classification:** verified issue

DX bullet 3 states the renderer places `screen_instructions` "before
highlights and actions, so the agent reads task framing before it reads the
items." This implies `screen_instructions` is the first thing in the rendered
output.

The confirmed rendering order is: View state → screen_instructions →
Highlights → (Actions). `screen_instructions` is not first — a "View state"
block precedes it. The agent reads View state before it reads
`screen_instructions`.

This matters for the DX promise: a developer who sets `screen_instructions`
expecting it to anchor the agent's reading context is actually placing it
after an automatically generated View state block whose structure is not
described anywhere in VISION. The factual rendering order should be stated,
or bullet 3 should be corrected to say "after View state and before
highlights."

---

### C3 — "Bootstrap skills / SKILL.md" non-responsibility imports femtobot-specific vocabulary

**Classification:** verified issue

The "What the library does not do" section states:

> "Detailed operating instructions for complex screen families belong in
> SKILL.md files loaded via the agent's bootstrap mechanism."

`SKILL.md` is a file-layout convention from femtobot, not a general
Python-library concept or an industry standard. A developer using a different
agent framework (LangGraph, CrewAI, a custom orchestrator) gets a prescriptive
pointer to a framework-specific artifact they have no concept of.

This item answers a femtobot-specific concern. It belongs in femtobot
documentation. In the library VISION it should either be generalized ("belongs
in your agent framework's bootstrap configuration, not in this library") or
removed. As written, it is a layer boundary violation: the library's VISION is
adopting the consuming application's vocabulary to explain what the library
does not do.

---

## Lower-priority findings

### L1 — Dict-key guarantee is unverifiable and potentially false

**Classification:** bounded concern (conditional verified issue)

The "Design constraints" section claims frozen dataclasses + `tuple[...]`
collection fields allow screens to be "used as dict keys." This is a
hashability guarantee.

The mechanism closes the hashability gap for collection fields by specifying
`tuple[...]` instead of `list`. However:

1. The VISION mentions a `metadata` field that is "not rendered at all."
   If `metadata` is typed as `dict[str, Any]` (a natural choice for
   unstructured carry-along data), then `DashboardScreen.__hash__()` will
   raise `TypeError` at runtime despite the dataclass being frozen. The
   dict-key claim would be false for any screen carrying metadata.

2. The VISION does not state the types of any scalar fields, so the
   guarantee is not self-verifiable from this document alone.

The claim should be qualified ("screens with hashable field values can be
used as dict keys") or the field type constraints needed to make the guarantee
unconditional should be stated (e.g., "all fields, including `metadata`, are
constrained to hashable types").

---

### L2 — DX bullet 5 ("Extend privately") describes a consumer-side pattern, not a library property

**Classification:** bounded concern

DX bullet 5 states developers can "extend privately by keeping
application-specific fields in their own dataclass and converting to the
library type at rendering time." The library has no extension mechanism,
converter protocol, or adapter interface that supports this. The library is
simply silent on consumer-internal structure.

Presenting consumer-side freedom as a DX property of the library overstates
what the library offers. A developer could reasonably ask "where is the
conversion hook?" and find nothing. The bullet would be more accurate as a
usage note ("no subclassing or registration means your own dataclass can
freely coexist and convert at rendering time") than as a DX capability claim.

---

### L3 — `session_complete` vocabulary in the dynamic-navigation-policy non-responsibility

**Classification:** speculative concern

The non-responsibility item for "Dynamic navigation policy" uses `session_complete`
as an example action name. This is femtobot vocabulary. A developer unfamiliar
with femtobot reads a non-responsibility framed around an unknown domain term.
Lower severity than C3 because it appears only in an example, not as a
prescriptive pointer.

---

### L4 — DX section provides no field-level orientation for any of the three dataclasses

**Classification:** bounded concern

The DX section mentions "the three dataclasses" and references two specific
fields (`screen_instructions`, `requires_approval`). It does not describe what
a `DashboardHighlight` contains, what fields `DashboardActionRef` has beyond
`requires_approval`, or what top-level fields `DashboardScreen` exposes
(beyond `screen_instructions`).

The golden-path promise ("no documentation beyond the type signatures") depends
on type signatures being legible at a glance. For a VISION document to support
that promise, it should at minimum name the principal fields of each type so a
reader can orient before reaching the API reference. The absence makes the DX
section feel incomplete relative to its own stated goal.

---

## Recommendations

**R1:** Add a DX sub-bullet or note to bullet 2 explaining `token_budget` semantics:
approximate tokens → character budget via `max(32, token_budget * 4)`,
output may be shorter than input, truncated output carries a `"... [truncated]"` marker.

**R2:** Correct bullet 3 to state the rendering order explicitly: View state appears
before `screen_instructions`, so the agent reads workspace state before task framing.

**R3:** Replace the `SKILL.md` reference in "What the library does not do" with a
framework-agnostic statement (e.g., "belongs in your agent framework's bootstrap
configuration").

**R4:** Qualify the dict-key claim in "Design constraints" or confirm that `metadata`
and all other fields are constrained to hashable types, with the constraint stated here.

**R5:** Reframe DX bullet 5 as a usage freedom rather than a DX capability
(the library imposes no coupling, so consumer dataclasses can freely coexist).

---

## Compact ledger

**Target document:** `/Users/thunderbird/Projects/agent-dashboard/design/VISION.md` (version 2)

**Focus used:** Internal consistency and completeness of DX vision; contradictions between
"What the library does not do" / "Design constraints" and rest of document; missing DX
properties; items misattributed to library layer.

**Main findings:**
- C1: `token_budget` and truncation absent from DX section — the renderer's principal
  behavioral parameter is not mentioned anywhere in the developer experience description.
- C2: `screen_instructions` implied to be first in rendered output; it is preceded by
  View state, making bullet 3 factually inaccurate about agent reading order.
- C3: `SKILL.md` reference in non-responsibilities is femtobot-specific vocabulary
  appearing in a general library document — layer boundary violation.
- L1: Dict-key hashability guarantee unverifiable; potentially false if `metadata`
  is typed as `dict`.
- L2: DX bullet 5 presents consumer-side freedom as a library DX capability.
- L3: `session_complete` example is femtobot vocabulary in a general library document.
- L4: No field-level orientation for any of the three dataclasses in the DX section.

**Ordered fix list for repair round:**

1. (C1) Add `token_budget` and truncation semantics to the DX section — at minimum,
   name the parameter, state the 4× char multiplier approximation, and note the
   truncation marker.

2. (C2) Correct DX bullet 3 to accurately state the rendering order: View state
   precedes `screen_instructions`; the bullet should not imply `screen_instructions`
   is the first thing the agent reads.

3. (C3) Generalize or remove the `SKILL.md` reference in "What the library does not do";
   replace with a framework-agnostic statement about bootstrap configuration.

4. (L1) Qualify the dict-key claim in "Design constraints" or state the type constraint
   on `metadata` and all other fields that makes the guarantee hold unconditionally.

5. (L2) Reframe DX bullet 5 from a capability claim to a usage freedom statement.

6. (L3) Generalize or remove the `session_complete` example in the dynamic-navigation-policy
   non-responsibility.
