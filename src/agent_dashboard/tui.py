from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from agent_dashboard.hub import ScreenHub
from agent_dashboard.renderer import render_screen


async def live_tui(hub: ScreenHub, *, token_budget: int = 4000) -> None:
    try:
        from rich.live import Live
        from rich.text import Text
    except ImportError as exc:
        raise ImportError(
            "live_tui requires the 'tui' extra: pip install agent-dashboard[tui]"
        ) from exc

    with Live("", refresh_per_second=4) as live:
        async for screen, _ in hub.subscribe_from_latest():
            live.update(Text(render_screen(screen, token_budget=token_budget)))


@asynccontextmanager
async def live_tui_context(hub: ScreenHub, *, token_budget: int = 4000) -> AsyncGenerator[None]:
    task = asyncio.create_task(live_tui(hub, token_budget=token_budget))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError, StopAsyncIteration:
            pass
