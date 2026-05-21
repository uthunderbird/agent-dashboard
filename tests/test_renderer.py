import pytest

from agent_dashboard import (
    DashboardActionRef,
    DashboardHighlight,
    DashboardScreen,
    render_screen,
)


def _minimal_screen(**kwargs) -> DashboardScreen:
    defaults = dict(
        dashboard_id="test",
        screen_id="s1",
        breadcrumb=("Root",),
        item_count=0,
        body_lines=(),
    )
    defaults.update(kwargs)
    return DashboardScreen(**defaults)


# --- purity / determinism ---


def test_same_input_same_output():
    screen = _minimal_screen(item_count=1, body_lines=("line",))
    assert render_screen(screen) == render_screen(screen)


# --- output structure ---


def test_header_lines_present():
    screen = _minimal_screen(item_count=3, breadcrumb=("A", "B"))
    out = render_screen(screen)
    assert "Attention items: 3" in out
    assert "Breadcrumb: A > B" in out
    assert "View state: collapsed" in out


def test_view_state_expanded_rendered_verbatim():
    screen = _minimal_screen(view_state="expanded")
    assert "View state: expanded" in render_screen(screen)


def test_screen_instructions_inserted_after_view_state():
    screen = _minimal_screen(screen_instructions="Do X first.")
    out = render_screen(screen)
    vs_pos = out.index("View state:")
    si_pos = out.index("Do X first.")
    assert si_pos > vs_pos


def test_screen_instructions_before_highlights():
    # ADR-0006 / P-11: screen_instructions renders between View state: and Highlights:.
    h = DashboardHighlight(highlight_id="h1", title="Urgent", summary="Act now", severity="high")
    screen = _minimal_screen(screen_instructions="Do X first.", highlights=(h,))
    out = render_screen(screen)
    si_pos = out.index("Do X first.")
    hl_pos = out.index("Highlights:")
    vs_pos = out.index("View state:")
    assert vs_pos < si_pos < hl_pos


def test_screen_instructions_none_not_rendered():
    # ADR-0006 I-4: None → field entirely absent, no blank line gap after View state:.
    screen = _minimal_screen(screen_instructions=None)
    out = render_screen(screen)
    assert "None" not in out
    assert "View state: collapsed\n\n" not in out


def test_screen_instructions_verbatim_content():
    # P-11: renderer must not modify screen_instructions — unicode and special
    # chars must pass through unchanged.
    instructions = "Prioritise high-severity items — respond before snoozing. ✓"
    out = render_screen(_minimal_screen(screen_instructions=instructions))
    assert instructions in out


def test_highlights_rendered():
    h = DashboardHighlight(highlight_id="h1", title="Overdue", summary="3 items", severity="high")
    screen = _minimal_screen(highlights=(h,))
    out = render_screen(screen)
    assert "Highlights:" in out
    assert "[high/active]" in out
    assert "Overdue" in out
    assert "3 items" in out


def test_highlight_non_default_status_rendered():
    # Renderer uses h.status verbatim; non-default value must appear in output.
    h = DashboardHighlight(
        highlight_id="h1", title="T", summary="S", severity="high", status="resolved"
    )
    assert "[high/resolved]" in render_screen(_minimal_screen(highlights=(h,)))


def test_highlight_suggested_next_step_rendered():
    h = DashboardHighlight(
        highlight_id="h1",
        title="T",
        summary="S",
        severity="low",
        suggested_next_step="reply now",
    )
    screen = _minimal_screen(highlights=(h,))
    assert "next: reply now" in render_screen(screen)


def test_highlight_no_suggested_next_step_omitted():
    h = DashboardHighlight(highlight_id="h1", title="T", summary="S", severity="low")
    assert "next:" not in render_screen(_minimal_screen(highlights=(h,)))


def test_body_lines_rendered():
    screen = _minimal_screen(body_lines=("line one", "line two"))
    out = render_screen(screen)
    assert "line one" in out
    assert "line two" in out


def test_screen_actions_section():
    a = DashboardActionRef(action_id="reply", label="Reply", kind="action")
    screen = _minimal_screen(screen_actions=(a,))
    out = render_screen(screen)
    assert "Screen actions:" in out
    assert "reply: Reply" in out


def test_tool_calls_section():
    a = DashboardActionRef(action_id="send", label="Send", kind="tool")
    screen = _minimal_screen(tool_calls=(a,))
    out = render_screen(screen)
    assert "Tool calls:" in out
    assert "send: Send" in out


def test_both_action_lists_populated_order_and_isolation():
    # ADR-0004: screen_actions renders before tool_calls; each action appears
    # only under its own section header.
    sa = DashboardActionRef(action_id="snooze", label="Snooze", kind="local")
    tc = DashboardActionRef(action_id="reply", label="Reply", kind="send_message")
    out = render_screen(_minimal_screen(screen_actions=(sa,), tool_calls=(tc,)))
    sa_pos = out.index("Screen actions:")
    tc_pos = out.index("Tool calls:")
    assert sa_pos < tc_pos
    # isolation: each action_id appears exactly once, under the right section
    sa_section = out[sa_pos:tc_pos]
    tc_section = out[tc_pos:]
    assert "snooze" in sa_section and "reply" not in sa_section
    assert "reply" in tc_section and "snooze" not in tc_section


def test_empty_screen_actions_omits_section():
    screen = _minimal_screen()
    assert "Screen actions:" not in render_screen(screen)


def test_empty_tool_calls_omits_section():
    screen = _minimal_screen()
    assert "Tool calls:" not in render_screen(screen)


def test_empty_highlights_omits_section():
    # ADR-0002: dump-engine omits empty sections; highlights=() is no exception.
    # Consistent with screen_actions=() and tool_calls=() behaviour.
    screen = _minimal_screen()
    assert "Highlights:" not in render_screen(screen)


def test_empty_breadcrumb_renders_empty_label():
    # external-dev-api.md: breadcrumb=() → "Breadcrumb: " (empty, no separator)
    out = render_screen(_minimal_screen(breadcrumb=()))
    assert "Breadcrumb: \n" in out or out.endswith("Breadcrumb: ")


def test_dashboard_id_not_in_output():
    # dashboard_id and screen_id are routing identifiers — not rendered.
    out = render_screen(_minimal_screen(dashboard_id="secret-dash", screen_id="secret-screen"))
    assert "secret-dash" not in out
    assert "secret-screen" not in out


def test_highlight_source_ref_not_rendered():
    # source_ref is a back-reference for consumer use; renderer ignores it.
    h = DashboardHighlight(
        highlight_id="h1", title="T", summary="S", severity="low", source_ref="msg-999"
    )
    assert "msg-999" not in render_screen(_minimal_screen(highlights=(h,)))


def test_view_state_does_not_change_body_content():
    # ADR-0002: view_state is informational — same body_lines render regardless.
    body = ("line one", "line two")
    collapsed = render_screen(_minimal_screen(view_state="collapsed", body_lines=body))
    expanded = render_screen(_minimal_screen(view_state="expanded", body_lines=body))
    assert "line one" in collapsed and "line one" in expanded
    assert "line two" in collapsed and "line two" in expanded
    # Only the View state line differs
    collapsed_lines = collapsed.splitlines()
    expanded_lines = expanded.splitlines()
    diffs = [(a, b) for a, b in zip(collapsed_lines, expanded_lines) if a != b]
    assert len(diffs) == 1
    assert diffs[0] == ("View state: collapsed", "View state: expanded")


# --- action formatting ---


def test_action_requires_approval_marker():
    # R-12: marker appears exactly once, on the approved action's line only.
    approved = DashboardActionRef(
        action_id="delete", label="Delete", kind="action", requires_approval=True
    )
    plain = DashboardActionRef(action_id="view", label="View", kind="action")
    out = render_screen(_minimal_screen(screen_actions=(approved, plain)))
    assert out.count("[requires approval]") == 1
    lines_with_marker = [ln for ln in out.splitlines() if "[requires approval]" in ln]
    assert len(lines_with_marker) == 1
    assert "delete" in lines_with_marker[0]


def test_action_no_approval_no_marker():
    a = DashboardActionRef(action_id="view", label="View", kind="action")
    assert "[requires approval]" not in render_screen(_minimal_screen(screen_actions=(a,)))


def test_action_requires_approval_position_relative_to_target_and_description():
    # external-dev-api.md line 167: [requires approval] appears after target
    # suffix and before description suffix.
    a = DashboardActionRef(
        action_id="reply",
        label="Reply",
        kind="send",
        target_source_id="inbox",
        target_item_id="msg-1",
        target_display_name="Message",
        requires_approval=True,
        description="Send a reply.",
    )
    out = render_screen(_minimal_screen(screen_actions=(a,)))
    line = next(ln for ln in out.splitlines() if "reply:" in ln)
    target_pos = line.index("[target=")
    approval_pos = line.index("[requires approval]")
    desc_pos = line.index(" — Send a reply.")
    assert target_pos < approval_pos < desc_pos


def test_rendering_symmetry_screen_actions_vs_tool_calls():
    # P-8: screen_actions and tool_calls use identical formatting logic.
    a = DashboardActionRef(
        action_id="send",
        label="Send",
        kind="tool",
        target_source_id="src",
        target_item_id="itm",
        target_display_name="Item",
        requires_approval=True,
        description="Send it.",
    )
    out_sa = render_screen(_minimal_screen(screen_actions=(a,)))
    out_tc = render_screen(_minimal_screen(tool_calls=(a,)))
    action_lines_sa = [ln for ln in out_sa.splitlines() if "send:" in ln]
    action_lines_tc = [ln for ln in out_tc.splitlines() if "send:" in ln]
    assert len(action_lines_sa) == 1 and len(action_lines_tc) == 1
    assert action_lines_sa[0] == action_lines_tc[0]


def test_action_target_rendered():
    a = DashboardActionRef(
        action_id="open",
        label="Open",
        kind="action",
        target_source_id="src",
        target_item_id="itm",
        target_display_name="Item",
    )
    out = render_screen(_minimal_screen(screen_actions=(a,)))
    assert "[target=src/itm:Item]" in out


def test_action_target_omitted_when_no_source():
    a = DashboardActionRef(action_id="open", label="Open", kind="action")
    assert "[target=" not in render_screen(_minimal_screen(screen_actions=(a,)))


def test_action_target_partial_fields_use_dash():
    a = DashboardActionRef(
        action_id="open",
        label="Open",
        kind="action",
        target_source_id="src",
    )
    out = render_screen(_minimal_screen(screen_actions=(a,)))
    assert "[target=src/-:-]" in out


def test_action_description_rendered():
    a = DashboardActionRef(
        action_id="reply", label="Reply", kind="action", description="Reply to sender"
    )
    assert "Reply to sender" in render_screen(_minimal_screen(screen_actions=(a,)))


def test_action_description_omitted_when_none():
    a = DashboardActionRef(action_id="reply", label="Reply", kind="action")
    out = render_screen(_minimal_screen(screen_actions=(a,)))
    assert " — " not in out


def test_metadata_not_rendered():
    a = DashboardActionRef(action_id="x", label="X", kind="action", metadata={"secret": "value"})
    assert "secret" not in render_screen(_minimal_screen(screen_actions=(a,)))


# --- truncation ---


def test_no_truncation_within_budget():
    screen = _minimal_screen()
    out = render_screen(screen, token_budget=4000)
    assert "... [truncated]" not in out


def test_truncation_applied_when_over_budget():
    screen = _minimal_screen(body_lines=("x" * 200,))
    out = render_screen(screen, token_budget=10)
    assert out.endswith("... [truncated]")


def test_truncation_deterministic():
    screen = _minimal_screen(body_lines=("y" * 500,))
    assert render_screen(screen, token_budget=5) == render_screen(screen, token_budget=5)


def test_truncation_minimum_budget():
    screen = _minimal_screen(body_lines=("z" * 1000,))
    out = render_screen(screen, token_budget=0)
    assert out.endswith("... [truncated]")
    assert len(out) <= 32 + 1  # marker fits in 32-char minimum


def test_truncation_negative_budget_does_not_raise():
    # ADR-0002: never raises for valid Python input; negative budget = min budget of 32 chars.
    screen = _minimal_screen(body_lines=("z" * 1000,))
    out = render_screen(screen, token_budget=-100)
    assert out.endswith("... [truncated]")


def test_action_empty_string_target_source_id_renders_suffix():
    # target_source_id="" is not None — suffix is rendered with empty source component.
    a = DashboardActionRef(action_id="x", label="X", kind="k", target_source_id="")
    out = render_screen(_minimal_screen(screen_actions=(a,)))
    assert "[target=/-:-]" in out


# --- DX rubric (external-dev-api.md R-2, R-3, R-8, R-9, R-10) ---


def _golden_path_screen() -> DashboardScreen:
    """Golden path screen from external-dev-api.md §golden path."""
    return DashboardScreen(
        dashboard_id="inbox",
        screen_id="summary",
        breadcrumb=("Inbox", "Today"),
        item_count=3,
        body_lines=("3 unread messages. 1 flagged. 0 pending approvals.",),
        view_state="collapsed",
        screen_instructions=(
            "Review the highlighted messages and respond to urgent items. "
            "Use a tool_call to reply or forward; use screen_actions to snooze "
            "or dismiss. Do not mark session complete while high-severity items remain."
        ),
        highlights=(
            DashboardHighlight(
                highlight_id="msg-42",
                title="Urgent: contract renewal",
                summary="Alice sent the draft for review.",
                severity="high",
                suggested_next_step="Open thread and review attachment.",
            ),
        ),
        screen_actions=(
            DashboardActionRef(
                action_id="snooze-msg-42",
                label="Snooze for 1 hour",
                kind="snooze",
            ),
        ),
        tool_calls=(
            DashboardActionRef(
                action_id="reply-msg-42",
                label="Reply to Alice",
                kind="send_message",
                description="Compose and send a reply in the thread.",
                requires_approval=True,
            ),
        ),
    )


def test_r2_golden_path_contains_required_strings_in_order():
    # R-2: golden path output contains "Urgent: contract renewal", "snooze-msg-42",
    # "reply-msg-42" in that order.
    out = render_screen(_golden_path_screen(), token_budget=2000)
    pos_highlight = out.index("Urgent: contract renewal")
    pos_snooze = out.index("snooze-msg-42")
    pos_reply = out.index("reply-msg-42")
    assert pos_highlight < pos_snooze < pos_reply


def test_r3_token_budget_10_within_char_limit():
    # R-3: token_budget=10 → char_budget=max(32,40)=40; output ≤ 40 + len marker + 1.
    screen = _golden_path_screen()
    out = render_screen(screen, token_budget=10)
    marker = "... [truncated]"
    assert len(out) <= 40 + len(marker) + 1
    # also must not raise — if we got here, it didn't


def test_r8_action_ref_minimal_construction_no_extra_suffixes():
    # R-8: DashboardActionRef with only action_id, label, kind renders without
    # target suffix or description suffix.
    a = DashboardActionRef(action_id="view", label="View item", kind="local")
    out = render_screen(_minimal_screen(screen_actions=(a,)))
    assert "[target=" not in out
    assert " — " not in out
    assert "[requires approval]" not in out


def test_r9_all_three_types_hashable():
    # R-9: all three data types are hashable and usable as dict keys / set members.
    h = DashboardHighlight(highlight_id="h1", title="T", summary="S", severity="low")
    a = DashboardActionRef(action_id="a1", label="L", kind="k")
    s = DashboardScreen(
        dashboard_id="d", screen_id="s", breadcrumb=("R",), item_count=0, body_lines=()
    )
    assert hash(h) == hash(h)
    assert hash(a) == hash(a)
    assert hash(s) == hash(s)
    # usable as dict keys
    d = {h: "highlight", a: "action", s: "screen"}
    assert d[h] == "highlight"
    assert d[a] == "action"
    assert d[s] == "screen"
    # usable in sets
    assert h in {h}
    assert a in {a}
    assert s in {s}


def test_r10_public_surface_importable_from_top_level():
    # R-10: all four public names importable from agent_dashboard without submodule imports.
    from agent_dashboard import (  # noqa: F401  (re-import is intentional)
        DashboardActionRef,
        DashboardHighlight,
        DashboardScreen,
        render_screen,
    )
    # If we reach here the import succeeded — that's the assertion.


def test_truncation_marker_on_own_line():
    screen = _minimal_screen(body_lines=("a" * 500,))
    out = render_screen(screen, token_budget=5)
    assert "\n... [truncated]" in out


# --- immutability ---


def test_screen_is_frozen():
    screen = _minimal_screen()
    with pytest.raises(Exception):
        screen.item_count = 99  # type: ignore[misc]


def test_action_ref_is_frozen():
    a = DashboardActionRef(action_id="x", label="X", kind="action")
    with pytest.raises(Exception):
        a.label = "Y"  # type: ignore[misc]


def test_highlight_is_frozen():
    h = DashboardHighlight(highlight_id="h", title="T", summary="S", severity="low")
    with pytest.raises(Exception):
        h.title = "Z"  # type: ignore[misc]
