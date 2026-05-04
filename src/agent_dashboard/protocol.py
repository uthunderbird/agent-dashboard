from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

SeverityLevel = Literal["high", "medium", "low", "info"]
StatusValue = Literal["active", "resolved"]
ViewState = Literal["collapsed", "expanded"]


@dataclass(frozen=True)
class DashboardHighlight:
    highlight_id: str
    title: str
    summary: str
    severity: str
    status: str = "active"
    source_ref: str | None = None
    suggested_next_step: str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DashboardActionRef:
    action_id: str
    label: str
    kind: str
    description: str | None = None
    target_source_id: str | None = None
    target_item_id: str | None = None
    target_display_name: str | None = None
    requires_approval: bool = False
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DashboardScreen:
    dashboard_id: str
    screen_id: str
    breadcrumb: tuple[str, ...]
    item_count: int
    body_lines: tuple[str, ...]
    view_state: ViewState = "collapsed"
    screen_instructions: str | None = None
    highlights: tuple[DashboardHighlight, ...] = field(default_factory=tuple)
    screen_actions: tuple[DashboardActionRef, ...] = field(default_factory=tuple)
    tool_calls: tuple[DashboardActionRef, ...] = field(default_factory=tuple)
