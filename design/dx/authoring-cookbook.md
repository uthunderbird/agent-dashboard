# Authoring Cookbook

This note captures practical conventions for people building
`DashboardScreen` values by hand or through an application renderer.

## Keep the boundary small

`agent-dashboard` owns the shared projection shape:

- what the agent reads (`render_screen()` output),
- stable ids for highlights and actions,
- optional metadata that consumers may inspect out of band,
- test helpers for asserting the projection.

It does not own rich HTML, frontend components, persistence, tool execution, or
consumer-specific state. Put those adapters in the consuming application.

## Do not parse display text

Avoid encoding machine data only in `summary`, `title`, or `body_lines` and then
parsing it back out in another layer. Those fields are optimized for agent
readability and can change for copy clarity.

Prefer stable fields:

```python
DashboardHighlight(
    highlight_id="category-electrical",
    title="Electrical",
    summary="2 outstanding defects",
    severity="high",
    metadata={
        "category_id": "category-electrical",
        "status": "in_progress",
        "open_defect_count": 2,
    },
)
```

The renderer ignores `metadata`, so this does not affect prompt text. Consumers
that need structured UI hints can read it explicitly.

## Model the selected item explicitly

For list-like screens, put the selected item in stable metadata rather than in
the display string alone:

```python
DashboardScreen(
    dashboard_id="gallery",
    screen_id="editing",
    breadcrumb=("Gallery",),
    item_count=len(figures),
    body_lines=(f"Selected figure: {selected_index + 1}",),
    highlights=tuple(
        DashboardHighlight(
            highlight_id=f"figure-{i + 1}",
            title=f"Figure {i + 1}",
            summary=f"{figure.shape} · {figure.color}",
            severity="high" if i == selected_index else "low",
            metadata={
                "position": i + 1,
                "selected": i == selected_index,
                "shape": figure.shape,
                "color": figure.color,
            },
        )
        for i, figure in enumerate(figures)
    ),
)
```

## Test projections directly

Use `agent_dashboard.testing` helpers for renderer tests:

```python
from agent_dashboard.testing import (
    assert_body_contains,
    assert_highlight_ids,
    assert_render_fits_budget,
    make_screen,
    screen_diff,
)

before = make_screen(item_count=1)
after = make_screen(item_count=2)
assert screen_diff(before, after).item_count_delta == 1

screen = render(state)
assert_highlight_ids(screen, ("category-electrical", "category-plumbing"))
assert_body_contains(screen, "Store #1610", "Phase: inspection")
agent_text = assert_render_fits_budget(screen, token_budget=512)
```

The assertion helpers are ordinary functions that raise `AssertionError`; they
do not import or depend on pytest.

## Keep custom UI adapters consumer-owned

If a rich UI needs fields that are not part of `DashboardScreen`, prefer a
consumer adapter that has access to the original state. Do not add display-only
fields to the core projection until multiple real consumers need the same
structure.

Good split:

- `render(state) -> DashboardScreen` for the shared agent-facing projection,
- consumer-owned `html_template(...) -> str` or frontend code for rich UI,
- tests that assert both the structured screen and the rich UI adapter.

This keeps the library transport-agnostic while still giving application
authors a practical path for polished interfaces.
