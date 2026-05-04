from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agent_dashboard.protocol import DashboardActionRef


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    label: str
    kind: str
    description: str | None = None
    requires_approval: bool = False

    def for_target(
        self,
        *,
        source_id: str,
        item_id: str | None = None,
        display_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> DashboardActionRef:
        return DashboardActionRef(
            action_id=self.action_id,
            label=self.label,
            kind=self.kind,
            description=self.description,
            requires_approval=self.requires_approval,
            target_source_id=source_id,
            target_item_id=item_id,
            target_display_name=display_name,
            metadata=metadata,
        )
