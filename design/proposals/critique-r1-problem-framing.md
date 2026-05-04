---
title: "Red-Team Critique — Round 1: Problem Framing Accuracy and Completeness"
target: VISION.md
round: 1 of 3
focus: Accuracy and completeness of the problem section
date: 2026-04-26
status: active
---

# Red-Team Critique — Round 1

**Target document:** `VISION.md`
**Focus:** Does the "The problem" section correctly identify the problems the library solves? Is there overclaiming (library claims to solve more than it does)? Underclaiming (real problems omitted)? Are the causal chains correct?

---

## CRITICAL FINDINGS

### C1 — Data/policy separation is implied as structural enforcement, not convention (verified issue)

**Location:** "The problem" section, the data/policy framing; "Design constraints" section, `screen_instructions` verbatim pass-through.

**What the document implies:** The problem section frames the data/policy distinction ("'What is here' is data... 'What to do' is policy") as a structural design achievement. A reader completing the problem section expects the library to enforce this separation at the type level.

**What the library actually provides:** `screen_instructions` is a single optional string field. The library renders it verbatim. Nothing prevents a consuming application from putting session-specific data into `screen_instructions` or putting stable policy into highlights. The separation is a naming convention and a usage recommendation, not a type-level invariant.

**Why it matters:** The document's central conceptual frame — the data/policy split — is the strongest rhetorical claim in the problem section. If it reads as a structural guarantee, readers and future contributors will be surprised to discover the library enforces nothing. This can also create confusion about how `screen_instructions` should be used in practice.

**Severity:** Critical. The data/policy frame is load-bearing for the document's argument.

---

### C2 — Agent-UX contract claim overstates what the library contracts (verified issue)

**Location:** "No agent-UX contract" bullet in "The problem" section.

**What the document says:** "The agent has no reliable way to know what an `action_id` means, which actions require approval, or what the screen expects it to do next."

**What the library solves:** Two of the three sub-problems named:
- Which actions require approval — solved via `requires_approval=True` / `[requires approval]` marker.
- What the screen expects next — addressed by `screen_instructions`.

**What the library does not solve:** `action_id` *meaning*. The library renders `action_id` verbatim from whatever the consuming application supplies. There is no schema, vocabulary, or constraint on what `action_id` values mean. This is explicitly a non-responsibility (field validation is listed in "What the library does not do").

**Why it matters:** Naming `action_id` meaning as a problem that the library implicitly addresses is inaccurate. An agent receiving a rendered screen still has no contracted understanding of `action_id` semantics — that contract must come from the consuming application or a companion convention. The problem section does not acknowledge this gap.

**Severity:** Critical. `action_id` meaning is architecturally outside the library's scope; presenting it as part of an "agent-UX contract" problem that this library solves is misleading.

---

### C3 — Multi-consumer divergence is the real portability problem; the document names a less precise proxy (verified issue)

**Location:** "No portability" bullet in "The problem" section.

**What the document says:** "A developer who builds a screen for one agent runtime cannot reuse it in another. The format is entangled with the runtime."

**What is actually the motivating problem:** The library was extracted from femtobot to serve a second consumer (a corporate project). The concrete problem is *multi-consumer divergence*: two codebases independently developing incompatible screen formats, making shared tooling, testing patterns, and institutional knowledge impossible to transfer. This is a developer-side coordination problem, not a runtime-portability problem.

**The gap:** Runtime portability (moving a screen from one agent runtime to another) is a narrower and less typical concern than multi-consumer reuse. The actual pain — two teams building screens that drift apart because there is no shared vocabulary — goes unnamed.

**Severity:** Critical. The portability claim names the wrong concrete problem. Readers building a second consumer will not recognize their pain in this framing.

---

## BOUNDED CONCERNS

### B1 — Opening framing positions the library as a "knowledge provider" for agents

**Location:** First paragraph of "The problem."

**What the document says:** "LLM agents... need to know two things at each step: what is here, and what to do."

**Concern:** The library produces text. Whether an agent "knows" something as a result of receiving that text depends on model behavior, prompt architecture, and session context — none of which the library controls. The "need to know" framing implies the library addresses the agent's knowledge state, which it cannot.

**Why bounded:** This is rhetorical rather than technically inaccurate in a way that causes downstream confusion. The problem section does not later claim the library ensures agent comprehension.

**Recommendation:** Reframe as "need to receive" or "applications need to present the agent with." Minor change, real precision improvement.

---

### B2 — Verbosity claim implies surgical scaffolding removal; the fix is truncation plus consistency

**Location:** "Verbosity" bullet in "The problem" section.

**What the document says:** "Token budget is wasted on scaffolding instead of content."

**What the library delivers:** Consistent format (no per-screen scaffolding variation) plus a total-size ceiling via `token_budget`. This does address scaffolding waste, but the mechanism is not surgical removal of scaffolding — it is structural consistency that eliminates *variation* in scaffolding, plus a hard budget ceiling.

**Why bounded:** The library's mechanism is a legitimate answer to the stated problem; the framing is imprecise but not misleading in a way that causes downstream decisions to go wrong.

---

## RECOMMENDATIONS (lower priority)

### R1 — Add multi-consumer reuse as a named problem

The real extraction driver — two teams building incompatible screen formats — should appear explicitly in the problem section. Suggested addition: a bullet noting that without a shared vocabulary, multiple applications independently invent incompatible screen representations, making shared tooling, patterns, and knowledge transfer impossible.

### R2 — Add testability as a named problem

Free-form prompt construction is difficult to test deterministically. Frozen dataclasses plus a pure renderer make screen construction and rendering fully unit-testable. This is a genuine developer pain point the library solves structurally; it goes unmentioned in the problem section.

### R3 — Add reproducibility/auditability as a named problem

The deterministic pure function means agent inputs are reproducible given the same screen data. Free-form prompt dumps are not reproducible in the same way. This is a real property the library delivers that the problem section does not identify as a pain point.

### R4 — Scope the agent-UX contract claim to what is actually contracted

Rewrite the "No agent-UX contract" bullet to name only the two sub-problems the library actually solves (approval status, task framing via `screen_instructions`) and omit `action_id` meaning, or explicitly note that action semantics remain the consumer's responsibility.

---

## LEDGER

| Field | Value |
|---|---|
| Target document | `VISION.md` — section "The problem" and its relationship to the stated solution |
| Focus | Problem framing accuracy and completeness (overclaiming, underclaiming, causal chain integrity) |
| Main findings | (C1) data/policy separation implied as structural; (C2) action_id semantics included in agent-UX contract claim but not solved; (C3) portability named as runtime concern, real problem is multi-consumer divergence; (B1) "need to know" language overstates library role; (B2) verbosity fix mechanism imprecisely framed |
| Ordered fix list | 1. Reframe data/policy separation as a usage convention/intent, not a structural enforcement. 2. Remove `action_id` meaning from the agent-UX contract claim, or explicitly scope it as outside library responsibility. 3. Replace or augment the portability bullet with multi-consumer divergence as the primary named problem. 4. Reframe the opening "need to know" language to "need to receive" or similar. 5. Add testability and reproducibility as named problems (lower priority). |
