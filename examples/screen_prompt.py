# Example: wrapping render_screen() in a promptstring for use with an LLM.
# pip install promptstrings
from __future__ import annotations

from agent_dashboard.protocol import DashboardScreen
from agent_dashboard.renderer import render_screen

from promptstrings import PromptContext, promptstring


@promptstring
def screen_context_prompt(screen_text: str) -> None:
    """You are managing an agent workspace. The current screen state is shown below.

    {screen_text}

    Respond only to what is visible on this screen."""


async def render_screen_prompt(screen: DashboardScreen, *, token_budget: int = 4000) -> str:
    """Render a DashboardScreen into a promptstring and return the resolved text."""
    rendered = render_screen(screen, token_budget=token_budget)
    ctx = PromptContext(values={"screen_text": rendered})
    return await screen_context_prompt.render(ctx)
