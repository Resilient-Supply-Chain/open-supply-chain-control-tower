from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import requests
import yaml
from langgraph.graph import END, StateGraph

import src.tools as tool_lib
from src.state import AgentState


def _load_prompt(project_root: Path) -> str:
    prompts_path = project_root / "config" / "prompts.yaml"
    prompts = yaml.safe_load(prompts_path.read_text(encoding="utf-8")) or {}
    return prompts.get("react_system_prompt", "")


def _load_llm_settings(project_root: Path) -> dict[str, Any]:
    settings_path = project_root / "config" / "settings.yaml"
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    return settings.get("llm", {})


def _call_local_llm(prompt: str, project_root: Path, timeout: int = 20) -> str:
    llm = _load_llm_settings(project_root)
    local = llm.get("local", {})
    endpoint = local.get("endpoint", "http://localhost:11434")
    model = local.get("model", "llama3.1:8b")
    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise ReAct agent."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    try:
        response = requests.post(
            f"{endpoint}/api/chat", json=chat_payload, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()
    except requests.HTTPError:
        # Fallback for Ollama versions that only support /api/generate.
        generate_payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        response = requests.post(
            f"{endpoint}/api/generate", json=generate_payload, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()


def _render_state_context(state: AgentState) -> str:
    steps = "\n".join([f"- {step}" for step in state.intermediate_steps]) or "None"
    thoughts = "\n".join(state.thought_history[-5:]) or "None"
    user_message = state.messages[-1][1] if state.messages else ""
    return (
        "Context:\n"
        f"User Message: {user_message}\n"
        f"Iteration: {state.iteration_count}\n"
        f"Intermediate Steps:\n{steps}\n"
        f"Thought History:\n{thoughts}\n"
    )


def _parse_model_output(model_output: str) -> tuple[str | None, dict[str, Any] | None, str | None]:
    action = None
    action_input = None
    final_answer = None
    for line in model_output.splitlines():
        if line.strip().startswith("Action:"):
            action = line.split("Action:", 1)[1].strip()
        if line.strip().startswith("Action Input:"):
            raw = line.split("Action Input:", 1)[1].strip()
            try:
                action_input = json.loads(raw)
            except json.JSONDecodeError:
                action_input = None
        if line.strip().startswith("Final Answer:"):
            final_answer = line.split("Final Answer:", 1)[1].strip()
    return action, action_input, final_answer


def _tool_registry() -> dict[str, Callable[..., Any]]:
    registry = {}
    for name in tool_lib.__all__:
        value = getattr(tool_lib, name, None)
        if callable(value):
            registry[name] = value
    return registry


def call_model(state: AgentState) -> AgentState:
    project_root = Path(__file__).resolve().parents[2]
    prompt = _load_prompt(project_root)
    context = _render_state_context(state)
    model_output = _call_local_llm(f"{prompt}\n\n{context}", project_root)

    state.last_model_output = model_output
    state.thought_history.append(model_output)
    state.iteration_count += 1

    action, action_input, final_answer = _parse_model_output(model_output)
    state.pending_action = action
    state.pending_action_input = action_input
    if final_answer:
        state.final_answer = final_answer
    return state


def _reflect_and_retry(
    *,
    state: AgentState,
    action: str,
    action_input: dict[str, Any],
    error_message: str,
    attempts: int = 3,
) -> tuple[bool, Any]:
    project_root = Path(__file__).resolve().parents[2]
    tool_map = _tool_registry()

    for _ in range(attempts):
        reflection_prompt = (
            "You encountered an error while calling a tool.\n"
            f"Tool: {action}\n"
            f"Action Input: {json.dumps(action_input)}\n"
            f"Error: {error_message}\n"
            "Provide a corrected Action and Action Input in the same format."
        )
        model_output = _call_local_llm(reflection_prompt, project_root)
        state.thought_history.append(model_output)
        new_action, new_input, final_answer = _parse_model_output(model_output)
        if final_answer:
            state.final_answer = final_answer
            return True, final_answer
        if not new_action or not isinstance(new_input, dict):
            continue
        action = new_action
        action_input = new_input
        tool_fn = tool_map.get(action)
        if not tool_fn:
            error_message = f"Unknown tool: {action}"
            continue
        try:
            result = tool_fn(**action_input)
            return True, result
        except Exception as exc:  # pragma: no cover - defensive
            error_message = str(exc)
    return False, error_message


def execute_tool(state: AgentState) -> AgentState:
    action = state.pending_action
    action_input = state.pending_action_input
    if not action:
        state.final_answer = "No action specified by the model."
        return state

    tool_map = _tool_registry()
    tool_fn = tool_map.get(action)
    if tool_fn is None:
        state.intermediate_steps.append((action, f"Unknown tool: {action}"))
        state.final_answer = f"Unknown tool: {action}"
        return state

    if not isinstance(action_input, dict):
        error_message = "Action Input must be valid JSON object."
        success, result = _reflect_and_retry(
            state=state,
            action=action,
            action_input=action_input or {},
            error_message=error_message,
        )
        state.intermediate_steps.append((action, result))
        if not success:
            state.final_answer = f"Tool error after retries: {result}"
        return state

    try:
        result = tool_fn(**action_input)
        state.intermediate_steps.append((action, result))
    except Exception as exc:  # pragma: no cover - defensive
        error_message = str(exc)
        success, result = _reflect_and_retry(
            state=state,
            action=action,
            action_input=action_input,
            error_message=error_message,
        )
        state.intermediate_steps.append((action, result))
        if not success:
            state.final_answer = f"Tool error after retries: {result}"
    return state


def route_next(state: AgentState) -> str:
    if state.final_answer:
        return "end"
    if state.pending_action:
        return "execute_tool"
    return "end"


def build_react_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("call_model", call_model)
    graph.add_node("execute_tool", execute_tool)
    graph.set_entry_point("call_model")
    graph.add_conditional_edges(
        "call_model",
        route_next,
        {"execute_tool": "execute_tool", "end": END},
    )
    graph.add_edge("execute_tool", "call_model")
    return graph.compile()


__all__ = ["build_react_graph"]

