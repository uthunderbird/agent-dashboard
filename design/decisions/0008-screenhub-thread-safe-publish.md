# 0008 — ScreenHub.publish() uses call_soon_threadsafe, not run_in_executor

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (hub-and-tui.md)
- **Supersedes:** —
- **Superseded by:** —

## Context

Agent code typically runs in a synchronous thread (or a thread pool) while the
event loop runs on a separate thread. `ScreenHub.publish()` must be safe to
call from any thread. Two asyncio primitives handle cross-thread
loop interaction: `loop.call_soon_threadsafe()` and
`loop.run_in_executor()`.

## Decision

`publish()` uses `loop.call_soon_threadsafe()` for each subscriber queue.
`run_in_executor()` is not used.

`publish()` is not marked `async` — it is a synchronous method callable from
any thread, including threads that have no event loop.

## Alternatives considered

- **`asyncio.run_in_executor()`** — schedules a callable on a thread pool.
  Rejected: `publish()` is a microsecond-scale operation (no I/O, no blocking,
  no computation). Thread pool overhead (task creation, executor dispatch,
  future resolution) would exceed the work itself. `run_in_executor` is
  appropriate for CPU-bound or blocking I/O work, not for enqueuing an object
  reference.
- **`async def publish()` with `await queue.put()`** — forces all callers into
  async context. Rejected: agent code in threads cannot `await`; requiring
  async publish would force consumers to build their own bridging layer.

## Consequences

- **Positive:** Synchronous callers in any thread can publish without
  bridging.
- **Positive:** Minimal overhead per publish; no executor allocation.
- **Negative:** `publish()` raises `RuntimeError` if called before a loop is
  attached (no silent failure). Consumers must ensure `ScreenHub` is used as
  an async context manager or `attach()` is called before publishing from
  threads.
- **Neutral:** Loop attachment is explicit: (1) via `async with ScreenHub()`
  (preferred), (2) automatic on first `subscribe()`, or (3) explicit
  `hub.attach(loop)`.

## Notes

`proposals/hub-and-tui.md` § "Thread-safe publish" and § "Loop attachment".
