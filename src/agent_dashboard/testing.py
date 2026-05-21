from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

from agent_dashboard.hub import ScreenHub
from agent_dashboard.protocol import DashboardActionRef, DashboardHighlight, DashboardScreen
from agent_dashboard.renderer import render_screen

_TRUNCATION_MARKER = "... [truncated]"


def make_screen(**overrides: Any) -> DashboardScreen:
    defaults: dict[str, Any] = {
        "dashboard_id": "test-dashboard",
        "screen_id": "test-screen",
        "breadcrumb": (),
        "item_count": 0,
        "body_lines": (),
    }
    defaults.update(overrides)
    return DashboardScreen(**defaults)


@dataclass(frozen=True)
class ScreenChangeSummary:
    highlights_added: tuple[DashboardHighlight, ...]
    highlights_removed: tuple[DashboardHighlight, ...]
    actions_added: tuple[DashboardActionRef, ...]
    actions_removed: tuple[DashboardActionRef, ...]
    item_count_delta: int
    view_state_changed: bool
    body_lines_changed: bool


def screen_diff(old: DashboardScreen, new: DashboardScreen) -> ScreenChangeSummary:
    old_all_actions = (*old.screen_actions, *old.tool_calls)
    new_all_actions = (*new.screen_actions, *new.tool_calls)

    return ScreenChangeSummary(
        highlights_added=tuple(h for h in new.highlights if h not in old.highlights),
        highlights_removed=tuple(h for h in old.highlights if h not in new.highlights),
        actions_added=tuple(a for a in new_all_actions if a not in old_all_actions),
        actions_removed=tuple(a for a in old_all_actions if a not in new_all_actions),
        item_count_delta=new.item_count - old.item_count,
        view_state_changed=old.view_state != new.view_state,
        body_lines_changed=old.body_lines != new.body_lines,
    )


def assert_highlight_ids(screen: DashboardScreen, expected: Sequence[str]) -> None:
    """Assert the screen exposes exactly the expected highlight ids in order."""

    actual = tuple(h.highlight_id for h in screen.highlights)
    expected_tuple = tuple(expected)
    assert actual == expected_tuple, (
        f"highlight ids differ: expected {expected_tuple!r}, got {actual!r}"
    )


def assert_action_ids(
    screen: DashboardScreen,
    expected: Sequence[str],
    *,
    channel: Literal["screen_actions", "tool_calls", "all"] = "all",
) -> None:
    """Assert action ids for one action channel or both channels together."""

    if channel == "screen_actions":
        actions = screen.screen_actions
    elif channel == "tool_calls":
        actions = screen.tool_calls
    else:
        actions = (*screen.screen_actions, *screen.tool_calls)

    actual = tuple(a.action_id for a in actions)
    expected_tuple = tuple(expected)
    assert actual == expected_tuple, (
        f"{channel} action ids differ: expected {expected_tuple!r}, got {actual!r}"
    )


def assert_body_contains(screen: DashboardScreen, *needles: str) -> None:
    """Assert every needle appears somewhere in the screen body lines."""

    body = "\n".join(screen.body_lines)
    missing = tuple(needle for needle in needles if needle not in body)
    assert not missing, f"body_lines missing {missing!r}; body was {body!r}"


def assert_render_fits_budget(screen: DashboardScreen, *, token_budget: int) -> str:
    """Render a screen and assert the output was not truncated.

    The rendered string is returned so tests can keep making ordinary substring
    assertions without calling ``render_screen`` a second time.
    """

    rendered = render_screen(screen, token_budget=token_budget)
    assert not rendered.endswith(_TRUNCATION_MARKER), (
        f"render_screen truncated output at token_budget={token_budget}"
    )
    return rendered


@asynccontextmanager
async def hub_context(
    *,
    maxsize: int = 16,
    overflow: Literal["drop_newest", "drop_oldest", "raise"] = "drop_newest",
    initial_screens: Sequence[tuple[DashboardScreen, str | None]] | None = None,
) -> AsyncGenerator[ScreenHub]:
    async with ScreenHub(maxsize=maxsize, overflow=overflow) as hub:
        if initial_screens:
            for screen, group_id in initial_screens:
                hub.publish(screen, group_id=group_id)
        yield hub
