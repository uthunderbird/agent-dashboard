"""
Tests for ADR-0001 and ADR-0003 invariants:
- hashability (conditional on metadata and collection field types)
- zero-asyncio on base import
- one-way dependency (no consumer imports in protocol/renderer)
- extension pattern: consumer dataclass + .to_library() pipeline
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from agent_dashboard import (
    DashboardActionRef,
    DashboardScreen,
)

# --- hashability ---


def test_action_ref_hashable_without_metadata():
    a = DashboardActionRef(action_id="x", label="X", kind="action")
    assert hash(a) == hash(a)


def test_action_ref_unhashable_with_dict_metadata():
    # ADR-0001: metadata=dict breaks hashability — documented caller-side invariant.
    a = DashboardActionRef(action_id="x", label="X", kind="action", metadata={"key": "val"})
    with pytest.raises(TypeError, match="unhashable"):
        hash(a)


def test_action_ref_hashable_with_none_metadata():
    a = DashboardActionRef(action_id="x", label="X", kind="action", metadata=None)
    assert hash(a) == hash(a)


def test_screen_hashable_with_tuple_fields():
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=("Root",),
        item_count=0,
        body_lines=("line",),
    )
    assert hash(screen) == hash(screen)


def test_screen_unhashable_with_list_body_lines():
    # ADR-0001: Python does not enforce tuple annotations at runtime.
    # Passing list to a tuple field silently breaks hashability.
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=("Root",),
        item_count=0,
        body_lines=["line"],  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="unhashable"):
        hash(screen)


def test_screen_unhashable_with_list_breadcrumb():
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=["Root"],  # type: ignore[arg-type]
        item_count=0,
        body_lines=(),
    )
    with pytest.raises(TypeError, match="unhashable"):
        hash(screen)


def test_screen_unhashable_with_unhashable_action_metadata():
    # ADR-0001 / P-3a: DashboardScreen containing an action with dict metadata
    # is unhashable — unhashability propagates through tuple field composition.
    action = DashboardActionRef(action_id="x", label="X", kind="k", metadata={"key": "val"})
    screen = DashboardScreen(
        dashboard_id="d",
        screen_id="s",
        breadcrumb=("Root",),
        item_count=0,
        body_lines=(),
        tool_calls=(action,),
    )
    with pytest.raises(TypeError, match="unhashable"):
        hash(screen)


# --- zero-asyncio on base import ---


def test_base_import_does_not_touch_asyncio():
    # ADR-0001: importing agent_dashboard must not load asyncio.
    # Run in a subprocess to get a clean sys.modules.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import agent_dashboard; import sys; "
            "assert 'asyncio' not in sys.modules, "
            "'asyncio loaded on base import: ' + str([k for k in sys.modules if \"asyncio\" in k])",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# --- one-way dependency ---


def _get_imports(path: Path) -> list[str]:
    """Return all top-level module names imported by a Python source file."""
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
    return names


def _src_root() -> Path:
    return Path(__file__).parent.parent / "src" / "agent_dashboard"


def test_protocol_does_not_import_consumer_modules():
    # ADR-0001 I-4: library code imports nothing from any consuming application.
    imports = _get_imports(_src_root() / "protocol.py")
    forbidden = {"femtobot", "agent_dashboard_corporate"}
    found = set(imports) & forbidden
    assert not found, f"protocol.py imports consumer modules: {found}"


def test_renderer_does_not_import_consumer_modules():
    imports = _get_imports(_src_root() / "renderer.py")
    forbidden = {"femtobot", "agent_dashboard_corporate"}
    found = set(imports) & forbidden
    assert not found, f"renderer.py imports consumer modules: {found}"


def test_protocol_stdlib_only():
    # protocol.py should only import from stdlib — it has zero runtime deps.
    imports = _get_imports(_src_root() / "protocol.py")
    stdlib_names = set(sys.stdlib_module_names)  # Python 3.10+
    third_party = [m for m in imports if m and m not in stdlib_names and m != "__future__"]
    assert not third_party, f"protocol.py has non-stdlib imports: {third_party}"


def test_renderer_stdlib_only():
    imports = _get_imports(_src_root() / "renderer.py")
    stdlib_names = set(sys.stdlib_module_names)
    # agent_dashboard is first-party (sibling module), not third-party
    first_party = {"agent_dashboard"}
    third_party = [
        m for m in imports if m and m not in stdlib_names and m not in first_party and m != "__future__"
    ]
    assert not third_party, f"renderer.py has non-stdlib imports: {third_party}"


# --- ADR-0003: extension pattern ---


def test_extension_pattern_to_library_produces_correct_action_ref():
    # ADR-0003: consumer defines own dataclass with extra fields and converts
    # to DashboardActionRef via .to_library() at the rendering boundary.
    from collections.abc import Mapping
    from dataclasses import dataclass as dc
    from typing import Any

    @dc(frozen=True)
    class ConsumerActionRef:
        action_id: str
        label: str
        kind: str
        description: str | None = None
        target_source_id: str | None = None
        target_item_id: str | None = None
        target_display_name: str | None = None
        requires_approval: bool = False
        metadata: Mapping[str, Any] | None = None
        # consumer-specific field not in DashboardActionRef
        routing_key: str | None = None

        def to_library(self) -> DashboardActionRef:
            return DashboardActionRef(
                action_id=self.action_id,
                label=self.label,
                kind=self.kind,
                description=self.description,
                target_source_id=self.target_source_id,
                target_item_id=self.target_item_id,
                target_display_name=self.target_display_name,
                requires_approval=self.requires_approval,
            )

    consumer_ref = ConsumerActionRef(
        action_id="reply",
        label="Reply",
        kind="send_message",
        requires_approval=True,
        routing_key="inbox-channel-42",  # consumer-specific, not sent to library
    )
    library_ref = consumer_ref.to_library()

    assert library_ref.action_id == "reply"
    assert library_ref.label == "Reply"
    assert library_ref.kind == "send_message"
    assert library_ref.requires_approval is True
    assert not hasattr(library_ref, "routing_key")


def test_extension_pattern_end_to_end_render():
    # ADR-0003: .to_library() output passes through render_screen correctly.
    from dataclasses import dataclass as dc

    @dc(frozen=True)
    class ConsumerActionRef:
        action_id: str
        label: str
        kind: str
        requires_approval: bool = False
        internal_id: int = 0  # consumer-specific

        def to_library(self) -> DashboardActionRef:
            return DashboardActionRef(
                action_id=self.action_id,
                label=self.label,
                kind=self.kind,
                requires_approval=self.requires_approval,
            )

    from agent_dashboard import DashboardScreen, render_screen

    ref = ConsumerActionRef(action_id="send", label="Send", kind="tool",
                            requires_approval=True, internal_id=99)
    screen = DashboardScreen(
        dashboard_id="d", screen_id="s", breadcrumb=("Root",),
        item_count=0, body_lines=(), tool_calls=(ref.to_library(),),
    )
    out = render_screen(screen)
    assert "send: Send" in out
    assert "[requires approval]" in out
    assert "99" not in out  # internal_id never reaches the renderer


def test_direct_construction_without_extension_pattern():
    # ADR-0003: direct DashboardActionRef construction is equally valid
    # when no consumer-specific typed fields are needed.
    from agent_dashboard import DashboardScreen, render_screen

    ref = DashboardActionRef(action_id="snooze", label="Snooze", kind="local")
    screen = DashboardScreen(
        dashboard_id="d", screen_id="s", breadcrumb=("Root",),
        item_count=0, body_lines=(), screen_actions=(ref,),
    )
    out = render_screen(screen)
    assert "snooze: Snooze" in out
