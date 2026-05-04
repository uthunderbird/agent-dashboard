---
title: Red-team critique — implementation and test coverage (v0.1)
date: 2026-04-26
scope: protocol.py, renderer.py, __init__.py, test_renderer.py (41), test_protocol.py (14) vs ADRs 0001–0003, external-dev-api.md
status: active
---

# Red-team critique: implementation and test coverage (v0.1)

## Summary

The `agent-dashboard` v0.1 implementation is **correct**. All 55 tests pass. No
ADR invariant is violated by the code. The principal finding is a **false
promise in a normative spec document** (`external-dev-api.md` P-3). Secondary
findings are bounded test coverage gaps — none of which indicate code bugs.

---

## F1 — Verified issue: `external-dev-api.md` P-3 overpromises hashability

**Location:** `external-dev-api.md`, line 303.

**Claim:**
> P-3. All-tuple collections. `breadcrumb`, `body_lines`, `highlights`,
> `screen_actions`, and `tool_calls` are `tuple[...]` types. They are always
> safe to iterate multiple times and **always hashable**.

**Reality:** The "always hashable" claim is false. A `DashboardScreen` with a
`DashboardActionRef(metadata={"key": "val"})` in `tool_calls` is unhashable —
because `metadata: Mapping[str, Any] | None` accepts dicts, and `frozen=True`
hashes by hashing all fields recursively. This is already documented in
ADR-0001 and tested in `test_action_ref_unhashable_with_dict_metadata` — but
the normative P-3 promise contradicts that documented caveat.

P-3 should say: "always safe to iterate multiple times" (true) and qualify
hashability: "hashable when all contained values are hashable." The tuple
structure is not the limiting factor; `metadata` is.

**Fix required:** Rewrite P-3 to remove the false absolute claim. Replace with:
> `breadcrumb`, `body_lines`, `highlights`, `screen_actions`, and `tool_calls`
> are `tuple[...]` types. They are always safe to iterate multiple times.
> Hashability depends on whether all contained values are hashable (see P-3a
> below).
> 
> **P-3a. Conditional hashability.** A `DashboardScreen` is hashable when all
> fields it contains are hashable. `metadata: Mapping[str, Any] | None` breaks
> hashability if the caller passes a `dict`. Callers who need hashable
> `DashboardActionRef` instances must use only hashable `metadata` values
> (e.g. `None`, a frozen dataclass, a named tuple).

---

## F2 — Bounded concern: `test_r9` gives false confidence on hashability

**Location:** `tests/test_renderer.py:test_r9_all_three_types_hashable`.

**Claim in test:** "R-9: all three data types are hashable and usable as dict
keys / set members."

**Reality:** The test uses only clean objects — all-string highlights, no
metadata on DashboardActionRef, simple tuple fields. It never tests that a
`DashboardScreen` containing `DashboardActionRef(metadata={"k": "v"})` is
unhashable. Combined with the false P-3 promise, this creates a coverage gap:
a developer could read P-3, read `test_r9`, and conclude that screens with
metadata-bearing actions are hashable — which is wrong.

**Fix:** Add a test `test_screen_unhashable_with_unhashable_action_metadata`
that constructs a screen with an action carrying dict metadata and asserts that
`hash(screen)` raises `TypeError`. This mirrors the existing
`test_action_ref_unhashable_with_dict_metadata` but tests it at the
`DashboardScreen` level (i.e., via composition through the tuple fields).

---

## F3 — Bounded concern: R-12 test checks presence, not "exactly once on correct line"

**Location:** `tests/test_renderer.py:test_action_requires_approval_marker`.

**R-12 spec claim:** "`[requires approval]` appears exactly once in the output,
on the correct action line."

**Current test:** `assert "[requires approval]" in render_screen(...)` —
asserts only presence, not count, not position.

**Risk:** If a renderer bug caused `[requires approval]` to appear on every
action line (not just the approved one), the current test would not catch it.

**Fix:** Strengthen to: render a screen with one approved and one non-approved
action; assert the marker appears exactly once; optionally assert it is on the
line containing the approved action's `action_id`.

---

## F4 — Bounded concern: P-8 rendering symmetry not explicitly tested

**Location:** `external-dev-api.md` P-8.

**P-8 claim:** "`screen_actions` and `tool_calls` MUST be rendered with
identical formatting logic."

**Current tests:** `test_screen_actions_section` and `test_tool_calls_section`
each test their own section independently, but never cross-assert that the same
action in both positions produces identical text.

**Risk:** If the renderer were refactored to use different helpers for the two
sections, P-8 would be violated without any test failing.

**Fix:** Add `test_rendering_symmetry_screen_actions_vs_tool_calls`: construct
an action ref, put it in `screen_actions` on one screen and `tool_calls` on
another, assert the rendered action lines are identical (strip the section
header, compare action-level output).

---

## F5 — Bounded concern: `DashboardHighlight.status` non-default value untested

**Location:** `renderer.py:_render_action` uses `[{h.severity}/{h.status}]`.

All tests use `status="active"` (the default). No test exercises a
non-default status value (e.g. `status="resolved"` → `[high/resolved]`).

**Risk:** If the renderer hardcoded `"active"` instead of using `h.status`,
no test would catch the regression.

**Fix:** Add `test_highlight_non_default_status_rendered` asserting that
`DashboardHighlight(..., status="resolved")` renders `[high/resolved]` (or
equivalent severity).

---

## F6 — Bounded concern: `screen_instructions` verbatim with special content untested

**Location:** `external-dev-api.md` P-11.

**P-11 claim:** renderer "MUST NOT modify, reformat, or independently truncate
`screen_instructions`."

**Current test:** `test_screen_instructions_inserted_after_view_state` only
checks position (after `View state:`, before body content). Never tests that
unusual content (newlines, unicode, leading/trailing spaces) passes through
verbatim.

**Risk:** If the renderer stripped or modified `screen_instructions` content,
no test would catch it.

**Fix:** Add `test_screen_instructions_verbatim_content` with a value that
contains a newline or unicode character; assert it appears exactly in the
output unchanged.

---

## F7 — Minor: output order summary at `external-dev-api.md` line 279 omits `screen_instructions`

**Location:** `external-dev-api.md` line 279.

**Claim:** "Output order: header fields → highlights → body lines → screen
actions → tool calls."

**Reality:** `screen_instructions` renders between `View state:` and
`Highlights:`. The order list omits it. (The field table at line 208 correctly
says "Rendered verbatim between `View state:` line and `Highlights:` section.")

**Fix:** Add `screen_instructions` to the output order description at line 279.

---

## What the implementation gets right

- **All 55 tests pass** with `uv run pytest`
- **Protocol correct:** all 3 frozen dataclasses match spec exactly
- **Renderer correct:** all field rendering matches spec; truncation algorithm matches spec
- **ADR-0001:** zero consumer imports ✓, stdlib-only ✓, zero asyncio on import ✓
- **ADR-0002:** pure function ✓, deterministic ✓, empty-section omission ✓, view_state informational ✓
- **ADR-0003:** `.to_library()` pattern tested end-to-end ✓, direct construction tested ✓
- **`__init__.py`:** exports exactly 4 names, `__all__` defined ✓

---

## Ordered fix list

| # | Finding | File | Action |
|---|---------|------|--------|
| F1 | P-3 false "always hashable" claim | `external-dev-api.md` | Rewrite P-3; add P-3a caveat |
| F2 | `test_r9` missing unhashable-via-composition test | `test_protocol.py` | Add `test_screen_unhashable_with_unhashable_action_metadata` |
| F3 | R-12 test partial | `test_renderer.py` | Strengthen to exactly-once + correct-line |
| F4 | P-8 symmetry untested | `test_renderer.py` | Add `test_rendering_symmetry_screen_actions_vs_tool_calls` |
| F5 | `status` non-default untested | `test_renderer.py` | Add `test_highlight_non_default_status_rendered` |
| F6 | `screen_instructions` verbatim untested | `test_renderer.py` | Add `test_screen_instructions_verbatim_content` |
| F7 | Output order description incomplete | `external-dev-api.md` line 279 | Add `screen_instructions` to order list |
