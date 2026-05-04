# 0012 — Custom serialization over dataclasses.asdict()

- **Status:** Accepted
- **Date:** 2026-04-26
- **Deciders:** Swarm design session (missing functionality session, I3)
- **Supersedes:** —
- **Superseded by:** —

## Context

Consumers that send screens over WebSocket or save them for test fixtures need
to serialize `DashboardScreen` to a dict (and deserialize back). The standard
library provides `dataclasses.asdict()`. The question was whether that
suffices or whether the library should provide its own serialization.

## Decision

`agent_dashboard.serialization` provides:

```python
def screen_to_dict(screen: DashboardScreen) -> dict[str, Any]
def screen_from_dict(data: dict[str, Any]) -> DashboardScreen
```

- `screen_to_dict`: converts all collection fields `tuple → list` for JSON
  compatibility; passes `metadata` through as-is.
- `screen_from_dict`: converts `list → tuple` for all collection fields;
  ignores unknown keys (forward-compatible with additive field evolution);
  raises on missing required fields; passes `metadata` through as-is.

## Alternatives considered

- **`dataclasses.asdict()` directly** — has two problems: (1) converts
  `tuple` to `list` but does not convert back on deserialization, so a
  round-tripped screen has `list` fields where `tuple` fields are expected;
  (2) behavior with `Mapping` fields (like `metadata`) is unpredictable.
  Rejected: consumers would need to write their own tuple restoration logic
  anyway; better to centralize it.
- **`dataclasses.asdict()` + consumer-side restoration** — every consumer
  re-implements the same `list → tuple` conversion. Rejected: this is exactly
  the kind of boilerplate the library should eliminate.
- **JSON schema / Pydantic validation on deserialization** — strict schema
  enforcement on `from_dict`. Rejected: additive field evolution means
  unknown keys from a newer version should be ignored, not raise. Strict
  validation would break consumers that serialize screens from a newer library
  version and deserialize with an older one.

## Consequences

- **Positive:** Round-trip fidelity: `screen_from_dict(screen_to_dict(s)) == s`
  for all valid screens.
- **Positive:** Forward-compatible: unknown fields added in future versions are
  silently ignored on deserialization.
- **Positive:** Zero extra dependencies; no Pydantic, no marshmallow.
- **Negative:** `metadata` is passed through as-is; hashability after
  deserialization is consumer responsibility (JSON decodes objects as dicts,
  which are not hashable).
- **Neutral:** No extras required; `serialization` is a base module.

## Notes

ROADMAP.md § "Accepted for implementation — I3".
