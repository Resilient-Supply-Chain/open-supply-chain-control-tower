from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import requests
import yaml
from langgraph.graph import END, StateGraph

import src.tools as tool_lib
from src.state import AgentState
from src.workflow.router import classify_intent
from src.agents.chatbot import friendly_chat_node


def _load_prompt(project_root: Path) -> str:
    prompts_path = project_root / "config" / "prompts.yaml"
    prompts = yaml.safe_load(prompts_path.read_text(encoding="utf-8")) or {}
    return prompts.get("react_system_prompt", "")


def _load_llm_settings(project_root: Path) -> dict[str, Any]:
    settings_path = project_root / "config" / "settings.yaml"
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    return settings.get("llm", {})


def _call_local_llm(
    prompt: str, project_root: Path, *, model_override: str | None = None, timeout: int = 20
) -> str:
    llm = _load_llm_settings(project_root)
    local = llm.get("local", {})
    endpoint = local.get("endpoint", "http://localhost:11434")
    model = model_override or local.get("model", "llama3.1:8b")
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
        try:
            response = requests.post(
                f"{endpoint}/api/generate", json=generate_payload, timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except Exception as exc:  # pragma: no cover - defensive
            return f"Local LLM error: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        return f"Local LLM error: {exc}"


def _collect_user_messages(state: AgentState, limit: int = 3) -> list[str]:
    messages = state.get("messages", [])
    user_messages: list[str] = []
    for item in messages:
        role = getattr(item, "type", None)
        if role == "human" and hasattr(item, "content"):
            user_messages.append(str(item.content))
        elif isinstance(item, tuple) and len(item) == 2:
            user_messages.append(str(item[1]))
    return user_messages[-limit:]


def _is_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _detect_user_language(state: AgentState) -> str:
    for msg in reversed(_collect_user_messages(state, limit=3)):
        if _is_cjk(msg):
            return "zh"
    return "en"


def _render_state_context(state: AgentState) -> str:
    steps = "\n".join([f"- {step}" for step in state.get("intermediate_steps", [])]) or "None"
    thoughts = "\n".join(state.get("thought_history", [])[-5:]) or "None"
    recent_user = _collect_user_messages(state, limit=3)
    user_message = recent_user[-1] if recent_user else ""
    combined_query = " | ".join(recent_user) if recent_user else "None"
    return (
        "Context:\n"
        f"User Message: {user_message}\n"
        f"Combined Query: {combined_query}\n"
        f"Iteration: {state.get('iteration_count', 0)}\n"
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


def _handle_timeout_or_followup(state: AgentState) -> AgentState:
    recent_user = _collect_user_messages(state, limit=3)
    combined_query = " | ".join(recent_user) if recent_user else ""
    language = _detect_user_language(state)
    followups = state.get("followup_count", 0)
    if followups >= 5:
        state["final_answer"] = "Sebastian is working on that!"
        state["pending_action"] = None
        return state
    followups += 1
    state["followup_count"] = followups
    if language == "zh":
        state["final_answer"] = (
            "\u6211\u9700\u8981\u66f4\u591a\u7ec6\u8282\u624d\u80fd\u7ee7\u7eed\uff0c"
            "\u6211\u4f1a\u628a\u4f60\u8865\u5145\u7684\u4fe1\u606f\u5408\u5e76\u7406\u89e3\u3002\n"
            f"\u5f53\u524d\u5df2\u77e5\uff1a{combined_query or '\uff08\u6682\u65e0\uff09'}\n\n"
            "\u8bf7\u8865\u5145\u4ee5\u4e0b\u8981\u70b9\uff1a\n"
            "- \u4f60\u60f3\u8981\u6211\u5b8c\u6210\u7684\u76ee\u6807\u662f\u4ec0\u4e48\uff1f\n"
            "- \u6709\u54ea\u4e9b\u8f93\u5165/\u6587\u4ef6/\u8def\u5f84\u6216\u7ea6\u675f\uff1f\n"
            "- \u4f60\u671f\u671b\u7684\u8f93\u51fa\u683c\u5f0f\u3001\u793a\u4f8b\u6216\u9a8c\u6536\u6807\u51c6\uff1f"
        )
    else:
        state["final_answer"] = (
            "I need a bit more detail to proceed, and I will merge any add-on details you provide.\n"
            f"Known so far: {combined_query or '(none)'}\n\n"
            "Please clarify:\n"
            "- What is the goal you want me to achieve?\n"
            "- What inputs/files/paths or constraints should I use?\n"
            "- What output format, example, or acceptance criteria do you expect?"
        )
    state["pending_action"] = None
    return state


def _check_runtime_limit(state: AgentState) -> bool:
    start_time = state.get("start_time")
    if start_time is None:
        state["start_time"] = time.monotonic()
        return False
    return (time.monotonic() - start_time) > 10


def call_model(state: AgentState) -> AgentState:
    project_root = Path(__file__).resolve().parents[2]
    print("🤖 Node: call_model")
    if _check_runtime_limit(state):
        return _handle_timeout_or_followup(state)
    prompt = _load_prompt(project_root)
    context = _render_state_context(state)
    model_output = _call_local_llm(
        f"{prompt}\n\n{context}",
        project_root,
        model_override=state.get("model_name"),
    )

    state["last_model_output"] = model_output
    if model_output.startswith("Local LLM error:"):
        return _handle_timeout_or_followup(state)
    state.setdefault("thought_history", []).append(model_output)
    state["iteration_count"] = state.get("iteration_count", 0) + 1

    action, action_input, final_answer = _parse_model_output(model_output)
    state["pending_action"] = action
    state["pending_action_input"] = action_input
    if action:
        state["final_answer"] = None
    elif final_answer:
        state["final_answer"] = final_answer
    return state


def friendly_chat(state: AgentState) -> dict:
    print("💬 Node: friendly_chat")
    return friendly_chat_node(state)


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
        model_output = _call_local_llm(
            reflection_prompt,
            project_root,
            model_override=state.get("model_name"),
        )
        if model_output.startswith("Local LLM error:"):
            return False, model_output
        state.setdefault("thought_history", []).append(model_output)
        new_action, new_input, final_answer = _parse_model_output(model_output)
        if final_answer:
            state["final_answer"] = final_answer
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
    print("🧰 Node: execute_tool")
    if _check_runtime_limit(state):
        return _handle_timeout_or_followup(state)
    action = state.get("pending_action")
    action_input = state.get("pending_action_input")
    if not action:
        return _handle_timeout_or_followup(state)

    tool_map = _tool_registry()
    tool_fn = tool_map.get(action)
    if tool_fn is None:
        state.setdefault("intermediate_steps", []).append((action, f"Unknown tool: {action}"))
        return _handle_timeout_or_followup(state)

    if not isinstance(action_input, dict):
        error_message = "Action Input must be valid JSON object."
        success, result = _reflect_and_retry(
            state=state,
            action=action,
            action_input=action_input or {},
            error_message=error_message,
        )
        state.setdefault("intermediate_steps", []).append((action, result))
        if not success:
            return _handle_timeout_or_followup(state)
        return state

    try:
        result = tool_fn(**action_input)
        state.setdefault("intermediate_steps", []).append((action, result))
        if isinstance(result, dict) and result.get("demo_url"):
            state["final_answer"] = (
                f"{result.get('message')}\n"
                f"Open the demo: {result.get('demo_url')}"
            )
    except Exception as exc:  # pragma: no cover - defensive
        error_message = str(exc)
        success, result = _reflect_and_retry(
            state=state,
            action=action,
            action_input=action_input,
            error_message=error_message,
        )
        state.setdefault("intermediate_steps", []).append((action, result))
        if not success:
            return _handle_timeout_or_followup(state)
    return state


def route_next(state: AgentState) -> str:
    if state.get("final_answer"):
        return "end"
    if state.get("pending_action"):
        return "execute_tool"
    return "end"


def build_react_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("friendly_chat", friendly_chat)
    graph.add_node("call_model", call_model)
    graph.add_node("execute_tool", execute_tool)
    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        lambda state: "friendly_chat" if state.get("intent") == "chat" else "call_model",
        {"friendly_chat": "friendly_chat", "call_model": "call_model"},
    )
    graph.add_edge("friendly_chat", END)
    graph.add_conditional_edges(
        "call_model",
        route_next,
        {"execute_tool": "execute_tool", "end": END},
    )
    graph.add_edge("execute_tool", "call_model")
    return graph.compile()


__all__ = ["build_react_graph"]

