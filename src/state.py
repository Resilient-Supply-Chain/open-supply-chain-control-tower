"""State schema for the ReAct-style agent workflow."""

from __future__ import annotations

from typing import Any, Annotated, List, Literal, Tuple, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """Typed state container for a ReAct loop."""

    messages: Annotated[List[Any], add_messages]
    intermediate_steps: List[Tuple[Any, Any]]
    thought_history: List[str]
    iteration_count: int
    final_answer: str | dict[str, Any] | None
    pending_action: str | None
    pending_action_input: dict[str, Any] | None
    last_model_output: str | None
    model_name: str | None
    intent: Literal["chat", "task"] | None
    start_time: float | None
    followup_count: int


__all__ = ["AgentState"]

