from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Literal

from agent_dashboard.protocol import DashboardScreen

_SENTINEL = object()

Event = tuple[DashboardScreen, str | None]


class ScreenHub:
    """Async reactive screen event hub.

    Publish DashboardScreen snapshots from any thread; async subscribers
    receive (screen, group_id) pairs. No diffs — every event is a full
    snapshot (ADR-0007). publish() is synchronous and thread-safe via
    call_soon_threadsafe (ADR-0008). group_id is an opaque consumer tag
    (ADR-0009). No persistence (ADR-0011).
    """

    def __init__(
        self,
        *,
        maxsize: int = 16,
        overflow: Literal["drop_newest", "drop_oldest", "raise"] = "drop_newest",
    ) -> None:
        self._maxsize = maxsize
        self._overflow = overflow
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queues: list[asyncio.Queue[object]] = []
        self._closed = False
        self._dropped = 0
        self._latest: Event | None = None

    # --- loop attachment ---

    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # --- publish ---

    def publish(self, screen: DashboardScreen, *, group_id: str | None = None) -> None:
        if self._closed:
            raise RuntimeError("ScreenHub is closed")
        if self._loop is None:
            raise RuntimeError(
                "ScreenHub has no event loop attached. "
                "Use 'async with ScreenHub()' or call hub.attach(loop) first."
            )
        event: Event = (screen, group_id)
        self._latest = event
        for q in list(self._queues):
            self._loop.call_soon_threadsafe(self._enqueue, q, event)

    def _enqueue(self, q: asyncio.Queue[object], event: Event) -> None:
        if self._overflow == "drop_newest":
            if q.full():
                self._dropped += 1
                return
            q.put_nowait(event)
        elif self._overflow == "drop_oldest":
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(event)
        else:  # "raise"
            if q.full():
                raise asyncio.QueueFull
            q.put_nowait(event)

    # --- subscribe ---

    async def subscribe(self) -> AsyncGenerator[Event]:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        q: asyncio.Queue[object] = asyncio.Queue(maxsize=self._maxsize)
        self._queues.append(q)
        try:
            while True:
                item = await q.get()
                if item is _SENTINEL:
                    break
                yield item  # type: ignore[misc]
        finally:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    async def subscribe_from_latest(self) -> AsyncGenerator[Event]:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        q: asyncio.Queue[object] = asyncio.Queue(maxsize=self._maxsize)
        if self._latest is not None:
            q.put_nowait(self._latest)
        self._queues.append(q)
        try:
            while True:
                item = await q.get()
                if item is _SENTINEL:
                    break
                yield item  # type: ignore[misc]
        finally:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    # --- dropped counter ---

    @property
    def dropped_count(self) -> int:
        return self._dropped

    def reset_dropped(self) -> None:
        self._dropped = 0

    # --- lifecycle ---

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        for q in list(self._queues):
            await q.put(_SENTINEL)

    async def __aenter__(self) -> ScreenHub:
        self._loop = asyncio.get_running_loop()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
