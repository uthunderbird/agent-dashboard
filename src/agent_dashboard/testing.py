from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

from agent_dashboard.hub import ScreenHub
from agent_dashboard.protocol import DashboardActionRef, DashboardHighlight, DashboardScreen


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
