# Example: minimal screen router for an agent loop.
#
# Pattern:
#   - screens are plain functions that return DashboardScreen
#   - a router maps screen_id → builder function
#   - the agent loop renders a screen, calls the LLM, parses the response,
#     and routes to the next screen
#   - unknown or invalid agent responses are handled gracefully (no crash)
#
# This file is intentionally domain-agnostic. Copy and adapt to your use case.
# The router holds no state itself — state lives in your domain objects.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from agent_dashboard import (
    ActionSpec,
    DashboardActionRef,
    DashboardHighlight,
    DashboardScreen,
    render_screen,
)

# ---------------------------------------------------------------------------
# Domain model (yours — not agent-dashboard's)
# ---------------------------------------------------------------------------

@dataclass
class TodoItem:
    id: str
    title: str
    done: bool
    priority: str  # "high" | "medium" | "low"


@dataclass
class AppState:
    items: list[TodoItem]
    selected_id: str | None = None


# ---------------------------------------------------------------------------
# Action specs (defined once, reused across screens)
# ---------------------------------------------------------------------------

SELECT   = ActionSpec(action_id="select",   label="Open",          kind="action")
COMPLETE = ActionSpec(action_id="complete", label="Mark complete",  kind="action")
DELETE   = ActionSpec(action_id="delete",   label="Delete",         kind="action", requires_approval=True)
BACK     = ActionSpec(action_id="back",     label="Back to list",   kind="action")


# ---------------------------------------------------------------------------
# Screen builders
# ---------------------------------------------------------------------------

def build_list_screen(state: AppState) -> DashboardScreen:
    pending = [t for t in state.items if not t.done]
    highlights = tuple(
        DashboardHighlight(
            highlight_id=t.id,
            title=t.title,
            summary=f"Priority: {t.priority}",
            severity=t.priority,
            suggested_next_step="Complete this task." if t.priority == "high" else None,
        )
        for t in pending
        if t.priority == "high"
    )
    return DashboardScreen(
        dashboard_id="todo",
        screen_id="list",
        breadcrumb=("Todo",),
        item_count=len(pending),
        body_lines=tuple(
            f'[{"x" if t.done else " "}] [{t.priority}] {t.title}'
            for t in state.items
        ),
        screen_instructions="Select a task to act on, or complete the highest-priority item.",
        highlights=highlights,
        screen_actions=tuple(
            SELECT.for_target(source_id="todo", item_id=t.id, display_name=t.title)
            for t in pending
        ),
    )


def build_detail_screen(state: AppState) -> DashboardScreen:
    item = next((t for t in state.items if t.id == state.selected_id), None)
    if item is None:
        # Selected item disappeared — fall back to list.
        return build_list_screen(state)
    return DashboardScreen(
        dashboard_id="todo",
        screen_id="detail",
        breadcrumb=("Todo", item.title),
        item_count=1,
        body_lines=(
            f"Title:    {item.title}",
            f"Priority: {item.priority}",
            f"Status:   {'done' if item.done else 'pending'}",
        ),
        screen_instructions="Complete or delete this task, or go back.",
        screen_actions=(
            COMPLETE.for_target(source_id="todo", item_id=item.id, display_name=item.title),
            DELETE.for_target(source_id="todo",   item_id=item.id, display_name=item.title),
            BACK.for_target(source_id="todo"),
        ),
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

# Maps screen_id → builder.  Add screens here as your app grows.
SCREENS: dict[str, Callable[[AppState], DashboardScreen]] = {
    "list":   build_list_screen,
    "detail": build_detail_screen,
}


@dataclass
class AgentAction:
    """Parsed agent response."""
    action_id: str
    target_item_id: str | None


def parse_agent_response(raw: dict[str, Any]) -> AgentAction | None:
    """Parse the agent's structured response. Returns None on malformed input."""
    action_id = raw.get("action_id")
    if not isinstance(action_id, str) or not action_id:
        return None
    return AgentAction(
        action_id=action_id,
        target_item_id=raw.get("target_item_id"),
    )


def apply_action(action: AgentAction, state: AppState) -> tuple[AppState, str]:
    """Apply action to state. Returns (new_state, next_screen_id).

    Returning the next screen_id from here is a deliberate design choice:
    the action handler knows where to go next. The router does not.
    """
    if action.action_id == "select":
        state.selected_id = action.target_item_id
        return state, "detail"

    if action.action_id == "complete":
        for item in state.items:
            if item.id == action.target_item_id:
                item.done = True
                break
        return state, "list"

    if action.action_id == "delete":
        state.items = [t for t in state.items if t.id != action.target_item_id]
        state.selected_id = None
        return state, "list"

    if action.action_id == "back":
        state.selected_id = None
        return state, "list"

    # Unknown action — stay on current screen, let the agent try again.
    return state, state.selected_id and "detail" or "list"


# ---------------------------------------------------------------------------
# Agent loop (stub — replace call_llm with your actual LLM call)
# ---------------------------------------------------------------------------

_stub_turn = 0

def call_llm(prompt: str) -> dict[str, Any]:
    """Stub: replace with your LLM call returning a structured response dict.

    This stub simulates: select t1 → complete t1 → complete t2 → complete t3.
    In a real application, call your LLM here and parse its structured output.
    """
    global _stub_turn
    responses = [
        {"action_id": "select",   "target_item_id": "t1"},
        {"action_id": "complete", "target_item_id": "t1"},
        {"action_id": "complete", "target_item_id": "t2"},
        {"action_id": "complete", "target_item_id": "t3"},
    ]
    response = responses[min(_stub_turn, len(responses) - 1)]
    _stub_turn += 1
    return response


def run(state: AppState, *, start_screen: str = "list", max_turns: int = 10) -> None:
    screen_id = start_screen

    for turn in range(max_turns):
        builder = SCREENS.get(screen_id)
        if builder is None:
            print(f"[router] Unknown screen_id {screen_id!r} — falling back to list")
            screen_id = "list"
            continue

        screen = builder(state)
        prompt = render_screen(screen, token_budget=1024)

        print(f"\n--- Turn {turn + 1} | screen={screen_id} ---")
        print(prompt)

        raw_response = call_llm(prompt)
        action = parse_agent_response(raw_response)

        if action is None:
            print("[router] Malformed agent response — retrying same screen")
            continue

        # Validate: is this action available on the current screen?
        available = {
            (a.action_id, a.target_item_id)
            for a in (*screen.screen_actions, *screen.tool_calls)
        }
        if (action.action_id, action.target_item_id) not in available:
            print(f"[router] Agent chose unavailable action {action!r} — retrying")
            continue

        state, screen_id = apply_action(action, state)

        # Stop when there's nothing left to do.
        if all(t.done for t in state.items):
            print("\n[router] All tasks complete.")
            break


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    state = AppState(items=[
        TodoItem("t1", "Publish agent-dashboard to PyPI", False, "high"),
        TodoItem("t2", "Write integration tests",         False, "medium"),
        TodoItem("t3", "Buy groceries",                   False, "low"),
    ])
    run(state, max_turns=5)
