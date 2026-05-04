from __future__ import annotations

from agent_dashboard.protocol import DashboardActionRef, DashboardScreen

_TRUNCATION_MARKER = "... [truncated]"


def render_screen(screen: DashboardScreen, *, token_budget: int = 4000) -> str:
    lines: list[str] = []

    breadcrumb = " > ".join(screen.breadcrumb) if screen.breadcrumb else ""
    lines.append(f"Attention items: {screen.item_count}")
    lines.append(f"Breadcrumb: {breadcrumb}")
    lines.append(f"View state: {screen.view_state}")

    if screen.screen_instructions is not None:
        lines.append(screen.screen_instructions)

    if screen.highlights:
        lines.append("Highlights:")
        for h in screen.highlights:
            lines.append(f"  - [{h.severity}/{h.status}] {h.title} — {h.summary}")
            if h.suggested_next_step is not None:
                lines.append(f"    next: {h.suggested_next_step}")

    for body_line in screen.body_lines:
        lines.append(body_line)

    if screen.screen_actions:
        lines.append("Screen actions:")
        for action in screen.screen_actions:
            lines.append(_render_action(action))

    if screen.tool_calls:
        lines.append("Tool calls:")
        for action in screen.tool_calls:
            lines.append(_render_action(action))

    rendered = "\n".join(lines)

    char_budget = max(32, token_budget * 4)
    if len(rendered) <= char_budget:
        return rendered

    cutoff = max(0, char_budget - len(_TRUNCATION_MARKER) - 1)
    return rendered[:cutoff].rstrip() + "\n" + _TRUNCATION_MARKER


def _render_action(action: DashboardActionRef) -> str:
    parts = [f"  - {action.action_id}: {action.label}"]

    if action.target_source_id is not None:
        item = action.target_item_id or "-"
        display = action.target_display_name or "-"
        parts.append(f" [target={action.target_source_id}/{item}:{display}]")

    if action.requires_approval:
        parts.append(" [requires approval]")

    if action.description is not None:
        parts.append(f" — {action.description}")

    return "".join(parts)
