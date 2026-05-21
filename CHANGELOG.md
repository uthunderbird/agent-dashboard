# Changelog

## 1.0.0 - 2026-05-21

First stable release of `agent-dashboard`.

### Added

- `ActionSpec` for reusable action definitions.
- `screen_to_dict()` and `screen_from_dict()` for explicit serialization.
- `ScreenHub` for async screen snapshot streaming.
- Optional Rich-based TUI helpers in `agent_dashboard.tui`.
- Testing helpers in `agent_dashboard.testing`:
  - `make_screen()`
  - `screen_diff()`
  - `assert_highlight_ids()`
  - `assert_action_ids()`
  - `assert_body_contains()`
  - `assert_render_fits_budget()`
  - `hub_context()`
- Human-facing authoring cookbook for practical projection, metadata, and
  testing patterns.

### Changed

- `DashboardHighlight.severity` and `DashboardHighlight.status` now use the
  exported `SeverityLevel` and `StatusValue` literal aliases for better
  IDE/type-checker feedback. Runtime behavior remains unchanged.
- README now documents the testing helpers and authoring patterns for keeping
  display text separate from structured metadata.

### Compatibility

- The 1.0.0 release keeps the runtime behavior of the core dataclasses and
  renderer intentionally small and stable.
- Literal annotations are for static feedback only; Python does not enforce
  them at runtime.
