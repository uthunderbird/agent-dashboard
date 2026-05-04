"""
Tests for ScreenHub covering ADRs 0007, 0008, 0009, 0011.
"""

import asyncio
import threading

import pytest

from agent_dashboard import DashboardScreen
from agent_dashboard.hub import ScreenHub


def _screen(n: int = 0) -> DashboardScreen:
    return DashboardScreen(
        dashboard_id="d",
        screen_id=f"s{n}",
        breadcrumb=("Root",),
        item_count=n,
        body_lines=(),
    )


# --- ADR-0007: full snapshot events, no diffs ---


async def test_subscriber_receives_full_snapshot():
    async with ScreenHub() as hub:
        received: list[tuple[DashboardScreen, str | None]] = []

        async def collect() -> None:
            async for event in hub.subscribe():
                received.append(event)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen(1))
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert len(received) == 1
    screen, group_id = received[0]
    assert screen.item_count == 1
    assert group_id is None


async def test_multiple_snapshots_received_in_order():
    async with ScreenHub() as hub:
        received: list[DashboardScreen] = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        for i in range(3):
            hub.publish(_screen(i))
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert [s.item_count for s in received] == [0, 1, 2]


# --- ADR-0008: synchronous publish via call_soon_threadsafe ---


async def test_publish_from_thread():
    async with ScreenHub() as hub:
        received: list[DashboardScreen] = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)

        def thread_target() -> None:
            hub.publish(_screen(42))

        t = threading.Thread(target=thread_target)
        t.start()
        t.join()
        await asyncio.sleep(0.05)
        await hub.aclose()
        await task

    assert len(received) == 1
    assert received[0].item_count == 42


async def test_publish_before_attach_raises():
    hub = ScreenHub()
    with pytest.raises(RuntimeError, match="no event loop"):
        hub.publish(_screen())


async def test_publish_after_close_raises():
    async with ScreenHub() as hub:
        pass
    with pytest.raises(RuntimeError, match="closed"):
        hub.publish(_screen())


# --- ADR-0009: group_id annotation ---


async def test_group_id_passed_through():
    async with ScreenHub() as hub:
        received: list[tuple[DashboardScreen, str | None]] = []

        async def collect() -> None:
            async for event in hub.subscribe():
                received.append(event)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen(), group_id="turn-7")
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert received[0][1] == "turn-7"


async def test_group_id_none_by_default():
    async with ScreenHub() as hub:
        received: list[tuple[DashboardScreen, str | None]] = []

        async def collect() -> None:
            async for event in hub.subscribe():
                received.append(event)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen())
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert received[0][1] is None


# --- ADR-0011: no persistence; stateless except queues ---


async def test_hub_has_no_screen_history():
    # Hub exposes no stored event history — only the latest snapshot and in-flight queues.
    async with ScreenHub() as hub:
        hub.publish(_screen(1))
        hub.publish(_screen(2))
    assert not hasattr(hub, "_history")


async def test_late_subscriber_misses_earlier_events():
    # ADR-0011: no replay. Late subscriber only gets events published after subscribe().
    async with ScreenHub() as hub:
        hub.publish(_screen(1))  # published before any subscriber

        received: list[DashboardScreen] = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen(2))  # published after subscriber
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert len(received) == 1
    assert received[0].item_count == 2


# --- subscribe_from_latest ---


async def test_subscribe_from_latest_receives_latest_immediately():
    async with ScreenHub() as hub:
        hub.publish(_screen(1))
        hub.publish(_screen(2))

        received: list[DashboardScreen] = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe_from_latest():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert len(received) == 1
    assert received[0].item_count == 2


async def test_subscribe_from_latest_no_prior_event():
    async with ScreenHub() as hub:
        received: list[DashboardScreen] = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe_from_latest():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen(7))
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert len(received) == 1
    assert received[0].item_count == 7


async def test_subscribe_from_latest_then_receives_new_events():
    async with ScreenHub() as hub:
        hub.publish(_screen(1))

        received: list[DashboardScreen] = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe_from_latest():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen(2))
        hub.publish(_screen(3))
        await asyncio.sleep(0)
        await hub.aclose()
        await task

    assert [s.item_count for s in received] == [1, 2, 3]


# --- overflow / dropped_count ---


async def test_drop_newest_increments_dropped_count():
    async with ScreenHub(maxsize=1, overflow="drop_newest") as hub:
        async def collect() -> None:
            async for _ in hub.subscribe():
                await asyncio.sleep(10)  # never drains

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen(1))  # fills queue
        hub.publish(_screen(2))  # dropped
        await asyncio.sleep(0)
        assert hub.dropped_count == 1
        hub.reset_dropped()
        assert hub.dropped_count == 0
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, StopAsyncIteration):
            pass


# --- multiple subscribers ---


async def test_multiple_subscribers_each_receive_event():
    async with ScreenHub() as hub:
        results: list[list[DashboardScreen]] = [[], []]

        async def collect(idx: int) -> None:
            async for screen, _ in hub.subscribe():
                results[idx].append(screen)

        t1 = asyncio.create_task(collect(0))
        t2 = asyncio.create_task(collect(1))
        await asyncio.sleep(0)
        hub.publish(_screen(99))
        await asyncio.sleep(0)
        await hub.aclose()
        await asyncio.gather(t1, t2)

    assert results[0][0].item_count == 99
    assert results[1][0].item_count == 99


# --- aclose terminates subscribers ---


async def test_aclose_terminates_subscriber():
    async with ScreenHub() as hub:
        received: list[DashboardScreen] = []

        async def collect() -> None:
            async for screen, _ in hub.subscribe():
                received.append(screen)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0)
        hub.publish(_screen(5))
        await asyncio.sleep(0)

    await task
    assert len(received) == 1


# --- zero-asyncio guarantee for base import ---


async def test_hub_not_imported_from_init():
    # ScreenHub must NOT be re-exported from agent_dashboard.__init__
    import agent_dashboard
    assert not hasattr(agent_dashboard, "ScreenHub")
