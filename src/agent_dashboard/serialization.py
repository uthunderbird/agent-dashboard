from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_dashboard.protocol import DashboardActionRef, DashboardHighlight, DashboardScreen


def screen_to_dict(screen: DashboardScreen) -> dict[str, Any]:
    return {
        "dashboard_id": screen.dashboard_id,
        "screen_id": screen.screen_id,
        "breadcrumb": list(screen.breadcrumb),
        "item_count": screen.item_count,
        "body_lines": list(screen.body_lines),
        "view_state": screen.view_state,
        "screen_instructions": screen.screen_instructions,
        "highlights": [_highlight_to_dict(h) for h in screen.highlights],
        "screen_actions": [_action_to_dict(a) for a in screen.screen_actions],
        "tool_calls": [_action_to_dict(a) for a in screen.tool_calls],
    }


def screen_from_dict(data: dict[str, Any]) -> DashboardScreen:
    return DashboardScreen(
        dashboard_id=data["dashboard_id"],
        screen_id=data["screen_id"],
        breadcrumb=tuple(data["breadcrumb"]),
        item_count=data["item_count"],
        body_lines=tuple(data["body_lines"]),
        view_state=data.get("view_state", "collapsed"),
        screen_instructions=data.get("screen_instructions"),
        highlights=tuple(_highlight_from_dict(h) for h in data.get("highlights", [])),
        screen_actions=tuple(_action_from_dict(a) for a in data.get("screen_actions", [])),
        tool_calls=tuple(_action_from_dict(a) for a in data.get("tool_calls", [])),
    )


def _highlight_to_dict(h: DashboardHighlight) -> dict[str, Any]:
    return {
        "highlight_id": h.highlight_id,
        "title": h.title,
        "summary": h.summary,
        "severity": h.severity,
        "status": h.status,
        "source_ref": h.source_ref,
        "suggested_next_step": h.suggested_next_step,
        "metadata": dict(h.metadata) if h.metadata is not None else None,
    }


def _highlight_from_dict(data: dict[str, Any]) -> DashboardHighlight:
    raw_meta = data.get("metadata")
    metadata: Mapping[str, Any] | None = raw_meta if raw_meta is not None else None
    return DashboardHighlight(
        highlight_id=data["highlight_id"],
        title=data["title"],
        summary=data["summary"],
        severity=data["severity"],
        status=data.get("status", "active"),
        source_ref=data.get("source_ref"),
        suggested_next_step=data.get("suggested_next_step"),
        metadata=metadata,
    )


def _action_to_dict(a: DashboardActionRef) -> dict[str, Any]:
    return {
        "action_id": a.action_id,
        "label": a.label,
        "kind": a.kind,
        "description": a.description,
        "target_source_id": a.target_source_id,
        "target_item_id": a.target_item_id,
        "target_display_name": a.target_display_name,
        "requires_approval": a.requires_approval,
        "metadata": dict(a.metadata) if a.metadata is not None else None,
    }


def _action_from_dict(data: dict[str, Any]) -> DashboardActionRef:
    raw_meta = data.get("metadata")
    metadata: Mapping[str, Any] | None = raw_meta if raw_meta is not None else None
    return DashboardActionRef(
        action_id=data["action_id"],
        label=data["label"],
        kind=data["kind"],
        description=data.get("description"),
        target_source_id=data.get("target_source_id"),
        target_item_id=data.get("target_item_id"),
        target_display_name=data.get("target_display_name"),
        requires_approval=data.get("requires_approval", False),
        metadata=metadata,
    )
