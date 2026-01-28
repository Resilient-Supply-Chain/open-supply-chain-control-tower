"""State schema for the ReAct-style agent workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple


@dataclass
class AgentState:
    """Mutable state container for a ReAct loop."""

    intermediate_steps: List[Tuple[Any, Any]] = field(default_factory=list)
    thought_history: List[str] = field(default_factory=list)
    iteration_count: int = 0
    final_answer: str | dict[str, Any] | None = None
    pending_action: str | None = None
    pending_action_input: dict[str, Any] | None = None
    last_model_output: str | None = None
    messages: List[Tuple[str, str]] = field(default_factory=list)


__all__ = ["AgentState"]

