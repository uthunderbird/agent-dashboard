import asyncio

from agent_dashboard import DashboardActionRef, DashboardHighlight, DashboardScreen
from agent_dashboard.testing import ScreenChangeSummary, hub_context, make_screen, screen_diff


# --- make_screen ---


def test_make_screen_returns_valid_screen():
    s = make_screen()
    assert isinstance(s, DashboardScreen)
    assert s.dashboard_id == "test-dashboard"
    assert s.item_count == 0


def test_make_screen_override_any_field():
    s = make_screen(dashboard_id="inbox", item_count=5, view_state="expanded")
    assert s.dashboard_id == "inbox"
    assert s.item_count == 5
    assert s.view_state == "expanded"


def test_make_screen_override_collections():
    h = DashboardHighlight(highlight_id="h1", title="T", summary="S", severity="high")
    s = make_screen(highlights=(h,))
    assert s.highlights == (h,)


# --- screen_diff ---


def _highlight(n: int) -> DashboardHighlight:
    return DashboardHighlight(
        highlight_id=f"h{n}", title=f"T{n}", summary=f"S{n}", severity="low"
    )


def _action(n: int) -> DashboardActionRef:
    return DashboardActionRef(action_id=f"a{n}", label=f"A{n}", kind="action")


def test_screen_diff_no_changes():
    s = make_screen()
    diff = screen_diff(s, s)
    assert diff == ScreenChangeSummary(
        highlights_added=(),
        highlights_removed=(),
        actions_added=(),
        actions_removed=(),
        item_count_delta=0,
        view_state_changed=False,
        body_lines_changed=False,
    )


def test_screen_diff_highlight_added():
    old = make_screen()
    new = make_screen(highlights=(_highlight(1),))
    diff = screen_diff(old, new)
    assert diff.highlights_added == (_highlight(1),)
    assert diff.highlights_removed == ()


def test_screen_diff_highlight_removed():
    old = make_screen(highlights=(_highlight(1),))
    new = make_screen()
    diff = screen_diff(old, new)
    assert diff.highlights_removed == (_highlight(1),)
    assert diff.highlights_added == ()


def test_screen_diff_action_added():
    old = make_screen()
    new = make_screen(screen_actions=(_action(1),))
    diff = screen_diff(old, new)
    assert diff.actions_added == (_action(1),)
    assert diff.actions_removed == ()


def test_screen_diff_action_removed_from_tool_calls():
    old = make_screen(tool_calls=(_action(1),))
    new = make_screen()
    diff = screen_diff(old, new)
    assert diff.actions_removed == (_action(1),)


def test_screen_diff_item_count_delta():
    old = make_screen(item_count=3)
    new = make_screen(item_count=7)
    assert screen_diff(old, new).item_count_delta == 4


def test_screen_diff_view_state_changed():
    old = make_screen(view_state="collapsed")
    new = make_screen(view_state="expanded")
    assert screen_diff(old, new).view_state_changed is True


def test_screen_diff_body_lines_changed():
    old = make_screen(body_lines=("a",))
    new = make_screen(body_lines=("b",))
    assert screen_diff(old, new).body_lines_changed is True


def test_screen_diff_body_lines_not_changed():
    s = make_screen(body_lines=("a", "b"))
    assert screen_diff(s, s).body_lines_changed is False


# --- hub_context ---


async def test_hub_context_yields_open_hub():
    async with hub_context() as hub:
        received = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(make_screen(item_count=1))
        await asyncio.sleep(0)

    await task
    assert len(received) == 1
    assert received[0].item_count == 1


async def test_hub_context_initial_screens():
    s1 = make_screen(item_count=1)
    s2 = make_screen(item_count=2)

    async with hub_context(initial_screens=[(s1, "g1"), (s2, None)]) as hub:
        received = []

        async def collect() -> None:
            async for event in hub.subscribe_from_latest():
                received.append(event)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)

    await task
    # subscribe_from_latest gives the last published (s2)
    assert received[0][0].item_count == 2


async def test_hub_context_closes_on_exit():
    async with hub_context() as hub:
        pass
    # publish after close should raise
    import pytest
    with pytest.raises(RuntimeError, match="closed"):
        hub.publish(make_screen())
