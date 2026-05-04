---
title: Red-team critique — VISION.md vs current implementation
date: 2026-04-26
scope: protocol.py, renderer.py, __init__.py vs VISION.md v4
status: active
---

# Red-team critique: VISION.md vs implementation (v0.1)

## Summary

Current implementation (`protocol.py` + `renderer.py`) correctly delivers on
the core promises of VISION.md: deterministic pure rendering, immutable data
model, one-way dependency, zero runtime deps. The principal failures are
**factual errors in code examples within VISION.md itself** — the golden path
sketch does not compile. Secondary findings are bounded concerns about
forward-looking claims and partial DX rubric coverage.

---

## P0 — Required fixes (code is wrong today)

### F1 — Golden path sketch: `DashboardHighlight` uses non-existent fields

**Location:** `VISION.md` § "The developer experience", pseudocode sketch.

**Claim:**
```python
highlights=(DashboardHighlight(label="Unread", value="3", severity="high"),),
```

**Reality:** `DashboardHighlight` has no `label` or `value` fields. Actual
required fields: `highlight_id: str`, `title: str`, `summary: str`,
`severity: str`. Running this code produces:
```
TypeError: DashboardHighlight.__init__() got an unexpected keyword argument 'label'
```

**Fix:** Replace with correct field names.

---

### F2 — Golden path sketch: `DashboardScreen` missing required fields

**Location:** Same pseudocode sketch.

**Claim:**
```python
screen = DashboardScreen(
    dashboard_id="inbox",
    screen_id="turn-42",
    screen_instructions="...",
    highlights=(...),
)
```

**Reality:** `DashboardScreen` has three additional required positional fields
with no defaults: `breadcrumb: tuple[str, ...]`, `item_count: int`,
`body_lines: tuple[str, ...]`. This code raises `TypeError` on construction.

**Fix:** Add missing fields. Corrected minimal working example (17 lines):

```python
from agent_dashboard import DashboardScreen, DashboardHighlight, render_screen

screen = DashboardScreen(
    dashboard_id="inbox",
    screen_id="turn-42",
    breadcrumb=("Inbox",),
    item_count=1,
    body_lines=(),
    screen_instructions="Reply to the oldest unread message first.",
    highlights=(DashboardHighlight(
        highlight_id="msg-1",
        title="Unread",
        summary="3 unread messages",
        severity="high",
    ),),
)
rendered = render_screen(screen, token_budget=512)
```

---

## Verified issues (correct but misleading)

### F3 — Rendering order description omits body_lines

**Location:** `VISION.md` § "The developer experience", bullet 3.

**Claim:** «rendering order is: View state → screen_instructions → Highlights
→ Actions»

**Reality:** Actual rendering order confirmed by running the renderer:
```
Attention items: {n}
Breadcrumb: ...
View state: ...
{screen_instructions}
Highlights:
  - ...
{body_lines[0]}
{body_lines[1]}
Screen actions:
  - ...
Tool calls:
  - ...
```

`body_lines` renders **between Highlights and Actions** — omitted entirely
from the VISION description. Any developer relying on this description to
understand prompt structure will have an incorrect mental model.

**Fix:** Add `body_lines` to the rendering order description.

---

## Bounded concerns (real but not P0)

### F4 — «Fifteen lines» claim vs reality

**Location:** `VISION.md` § "The developer experience".

**Claim:** «The golden path should take fifteen lines of code.»

**Reality:** Corrected minimal working example = 17 lines. Difference is
small and within spirit of the claim, but the specific number is off.

**Assessment:** Acceptable if corrected as part of fixing F1/F2. Not a
standalone blocker.

---

### F5 — «Transport-agnostic» claim without serialization in v0.1

**Location:** `VISION.md` § "What agent-dashboard provides".

**Claim:** The data model is «transport-agnostic». Implies screens can be
sent over any transport.

**Reality:** `screen_to_dict()` / `screen_from_dict()` are in the roadmap
(I3) but not implemented in v0.1. Sending a `DashboardScreen` over WebSocket
today requires consumer-written serialization. `dataclasses.asdict()` has
known issues with tuple→list conversion.

**Assessment:** VISION is a forward-looking document; this is an acceptable
gap *if* the claim is understood as directional, not a current promise. Risk:
a developer reading VISION today may assume serialization works out of the box.
Consider adding a version qualifier or a pointer to the roadmap.

---

### F6 — «No agent-UX contract» partially solved

**Location:** `VISION.md` § "The problem", bullet 3.

**Claim:** Library solves the agent-UX contract gap.

**Reality:** Library provides structural signals: `requires_approval`,
`screen_instructions`, `screen_actions` vs `tool_calls` separation. These
are real progress. However, `action_id` semantics remain consumer
responsibility — the agent sees `action_id="reply-msg-42"` without
knowing what executing it means. VISION acknowledges this explicitly
(`action_id` semantics are consumer responsibility). The claim is
**partially delivered** in v0.1 with the structural layer; semantic
layer is outside scope.

**Assessment:** Correctly scoped in VISION. No fix needed; the acknowledgment
is already in the text.

---

## DX rubric coverage (external-dev-api.md R-1 through R-12)

| Item | Coverage | Gap |
|------|---------|-----|
| R-1 | Not automatable (subjective UX claim) | — |
| R-2 | Partial — no golden-path-specific test | Add test using corrected sketch |
| R-3 | `test_truncation_applied_when_over_budget` (partial) | Assert exact char count |
| R-4 | `test_truncation_minimum_budget` ✓ | — |
| R-5 | `test_metadata_not_rendered` ✓ | — |
| R-6 | Both section-omit tests ✓ | — |
| R-7 | `test_view_state_does_not_change_body_content` ✓ | — |
| R-8 | `test_action_no_approval_no_marker` (partial) | Test with only 3 fields explicitly |
| R-9 | `test_screen_hashable_with_tuple_fields` (screen only) | Add highlight + action_ref hash tests |
| R-10 | Import test covers asyncio; no explicit 4-name import test | Add `from agent_dashboard import A,B,C,D` test |
| R-11 | `test_screen_instructions_inserted_after_view_state` ✓ | — |
| R-12 | Both approval tests ✓ | — |

**Uncovered R-items requiring action: R-2, R-3 (strengthen), R-8 (strengthen),
R-9 (extend to all three types), R-10 (add explicit import test).**

---

## What the implementation gets right

- **Pure rendering:** ✓ confirmed by tests and static analysis
- **Immutable data model:** ✓ `frozen=True`, tuple collections
- **One-way dependency:** ✓ confirmed by `test_protocol_stdlib_only` / consumer-import tests
- **Zero runtime deps:** ✓ `pyproject.toml` `dependencies = []`
- **`__all__` defined:** ✓ exactly 4 names
- **`py.typed` marker:** ✓ present
- **Non-responsibilities section:** ✓ fully matches implementation — no action execution, no state, no token counting, no field validation

---

## Ordered fix list

1. **[P0]** Fix `DashboardHighlight` field names in VISION golden path sketch (F1)
2. **[P0]** Add missing required fields to `DashboardScreen` in VISION sketch (F2)
3. **[P0]** Update «fifteen lines» count to match corrected sketch (F4, bundled with above)
4. **[verified]** Add `body_lines` to rendering order description in VISION (F3)
5. **[bounded]** Add version qualifier to transport-agnostic claim or roadmap pointer (F5)
6. **[test gap]** Add R-2 golden-path test, strengthen R-3, R-8, R-9, add R-10 explicit import test
