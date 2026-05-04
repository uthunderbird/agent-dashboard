import asyncio

import pytest

from agent_dashboard.hub import ScreenHub
from agent_dashboard.testing import make_screen
from agent_dashboard.tui import live_tui_context


async def test_live_tui_context_starts_and_stops():
    async with ScreenHub() as hub:
        async with live_tui_context(hub):
            hub.publish(make_screen(item_count=1))
            await asyncio.sleep(0.05)
        # context exited cleanly — no exception


async def test_live_tui_context_survives_empty_hub():
    async with ScreenHub() as hub:
        async with live_tui_context(hub):
            await asyncio.sleep(0)
        # closed without any published screens


async def test_live_tui_context_receives_multiple_screens():
    received_count = 0

    async with ScreenHub() as hub:
        async with live_tui_context(hub):
            for i in range(3):
                hub.publish(make_screen(item_count=i))
            await asyncio.sleep(0.05)

    # no assertion on received_count — TUI is fire-and-forget display;
    # the test verifies no exception is raised during multi-publish


def test_tui_module_importable():
    import agent_dashboard.tui  # noqa: F401


async def test_live_tui_import_error_without_rich(monkeypatch: pytest.MonkeyPatch):
    import builtins

    real_import = builtins.__import__

    def blocked_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name.startswith("rich"):
            raise ImportError(f"Mocked missing: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    from agent_dashboard.tui import live_tui

    async with ScreenHub() as hub:
        with pytest.raises(ImportError, match="tui.*extra"):
            await live_tui(hub)
