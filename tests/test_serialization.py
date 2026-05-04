from agent_dashboard import DashboardActionRef, DashboardHighlight, DashboardScreen
from agent_dashboard.serialization import screen_from_dict, screen_to_dict


def _full_screen() -> DashboardScreen:
    return DashboardScreen(
        dashboard_id="inbox",
        screen_id="turn-1",
        breadcrumb=("Root", "Inbox"),
        item_count=2,
        body_lines=("line one", "line two"),
        view_state="expanded",
        screen_instructions="Do the thing.",
        highlights=(
            DashboardHighlight(
                highlight_id="h1",
                title="Alert",
                summary="Something happened.",
                severity="high",
                status="active",
                source_ref="msg-42",
                suggested_next_step="Reply now.",
            ),
        ),
        screen_actions=(
            DashboardActionRef(
                action_id="reply",
                label="Reply",
                kind="action",
                description="Send a reply.",
                target_source_id="inbox",
                target_item_id="msg-42",
                target_display_name="Message 42",
                requires_approval=True,
                metadata={"priority": 1},
            ),
        ),
        tool_calls=(
            DashboardActionRef(
                action_id="fetch",
                label="Fetch",
                kind="tool",
            ),
        ),
    )


def test_round_trip_full_screen():
    screen = _full_screen()
    assert screen_from_dict(screen_to_dict(screen)) == screen


def test_to_dict_collections_are_lists():
    d = screen_to_dict(_full_screen())
    assert isinstance(d["breadcrumb"], list)
    assert isinstance(d["body_lines"], list)
    assert isinstance(d["highlights"], list)
    assert isinstance(d["screen_actions"], list)
    assert isinstance(d["tool_calls"], list)


def test_from_dict_collections_are_tuples():
    screen = screen_from_dict(screen_to_dict(_full_screen()))
    assert isinstance(screen.breadcrumb, tuple)
    assert isinstance(screen.body_lines, tuple)
    assert isinstance(screen.highlights, tuple)
    assert isinstance(screen.screen_actions, tuple)
    assert isinstance(screen.tool_calls, tuple)


def test_from_dict_ignores_unknown_fields():
    d = screen_to_dict(_full_screen())
    d["unknown_future_field"] = "some value"
    screen = screen_from_dict(d)
    assert screen.dashboard_id == "inbox"


def test_round_trip_minimal_screen():
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=(),
        item_count=0,
        body_lines=(),
    )
    assert screen_from_dict(screen_to_dict(screen)) == screen


def test_metadata_round_trip():
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=(),
        item_count=0,
        body_lines=(),
        screen_actions=(
            DashboardActionRef(
                action_id="a",
                label="A",
                kind="k",
                metadata={"x": 1, "y": "two"},
            ),
        ),
    )
    result = screen_from_dict(screen_to_dict(screen))
    assert result.screen_actions[0].metadata == {"x": 1, "y": "two"}


def test_none_metadata_round_trip():
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=(),
        item_count=0,
        body_lines=(),
        screen_actions=(
            DashboardActionRef(action_id="a", label="A", kind="k"),
        ),
    )
    result = screen_from_dict(screen_to_dict(screen))
    assert result.screen_actions[0].metadata is None


def test_highlight_metadata_round_trip():
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=(),
        item_count=0,
        body_lines=(),
        highlights=(
            DashboardHighlight(
                highlight_id="h1",
                title="T",
                summary="S",
                severity="low",
                metadata={"source": "db", "count": 3},
            ),
        ),
    )
    result = screen_from_dict(screen_to_dict(screen))
    assert result.highlights[0].metadata == {"source": "db", "count": 3}


def test_highlight_metadata_none_round_trip():
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=(),
        item_count=0,
        body_lines=(),
        highlights=(
            DashboardHighlight(highlight_id="h1", title="T", summary="S", severity="low"),
        ),
    )
    result = screen_from_dict(screen_to_dict(screen))
    assert result.highlights[0].metadata is None
