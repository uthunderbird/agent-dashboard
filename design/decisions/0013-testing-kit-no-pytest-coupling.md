# 0013 — Testing kit: no pytest coupling in the library

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (eval fixtures session)
- **Supersedes:** —
- **Superseded by:** —

## Context

Consumers writing tests against their own screen-building code need:
1. A factory for minimal valid `DashboardScreen` instances with sensible
   defaults and per-test overrides (`make_screen`).
2. Async setup/teardown for `ScreenHub`-based tests — open a hub, optionally
   pre-publish screens, yield, then close.

Three routes were evaluated: docs-only (README snippet), importable pytest
fixtures (`@pytest.fixture` decorated functions in `testing.py`), and a
pytest11 plugin entry point.

## Decision

`agent_dashboard.testing` provides:

```python
def make_screen(**overrides) -> DashboardScreen
    # Minimal valid screen with sensible defaults; any field overridable.

@asynccontextmanager
async def hub_context(
    *,
    maxsize: int = 16,
    overflow: Literal[...] = "drop_newest",
    initial_screens: Sequence[tuple[DashboardScreen, str | None]] | None = None,
) -> AsyncGenerator[ScreenHub, None]:
    # Opens ScreenHub, optionally publishes initial_screens, yields, closes.
```

`hub_context` is an async context manager helper, not a pytest fixture.
`pytest` is not imported anywhere in the library. `pytest-asyncio` is not a
library dependency.

Consumer wires it in their own `conftest.py`:
```python
from agent_dashboard.testing import hub_context

@pytest.fixture
async def hub():
    async with hub_context() as h:
        yield h
```

Consumer prerequisites: `pytest-asyncio` installed,
`asyncio_mode = "auto"` in `[tool.pytest.ini_options]`.

## Alternatives considered

- **Docs-only (README conftest snippet)** — zero maintenance burden at
  authoring time, but the snippet is untested by the library. If
  `ScreenHub`'s API changes, the snippet rots silently. Rejected.
- **Importable `@pytest.fixture` functions in `testing.py`** — requires
  `pytest` as a library import in `testing.py`. Adds `pytest-asyncio` to the
  `[testing]` extra. Rejected: the library should not carry test-runner
  concerns as dependencies; the async generator approach achieves the same
  non-rot benefit without the coupling.
- **`pytest11` entry point (auto-inject plugin)** — `hub` fixture
  auto-activates for any project installing `agent-dashboard[testing]`.
  Rejected: namespace pollution; every project gets fixtures injected whether
  they want them or not. Appropriate for `pytest-django` scale, not this library.

## Consequences

- **Positive:** `testing.py` has no `pytest` import; it is usable in any
  async test framework (anyio, unittest, custom runners).
- **Positive:** `hub_context` is exercised in the library's own test suite
  via `async with`; API changes break library tests before consumer tests.
- **Positive:** No fixture namespace pollution.
- **Negative:** Consumer must write two lines of conftest boilerplate.
  One-time cost per project.
- **Neutral:** `pytest-asyncio` and `asyncio_mode = "auto"` remain consumer
  prerequisites, documented in the README.

## Notes

ROADMAP.md § "Testing kit — I5+I4".
Eval fixtures Swarm session (2026-04-26).
