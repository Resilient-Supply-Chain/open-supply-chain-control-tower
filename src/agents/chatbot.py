from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Tuple

import yaml
import requests
import subprocess

from langchain_core.messages import AIMessage, HumanMessage
from src.state import AgentState
from src.tools.demo_runner import run_demo_presentation


@dataclass(frozen=True)
class ChatbotConfig:
    mode: str
    provider: str
    backend: str
    model: str
    endpoint: str
    system_prompt: str


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_chatbot_config(project_root: Path) -> ChatbotConfig:
    settings = _load_yaml(project_root / "config" / "settings.yaml")
    prompts = _load_yaml(project_root / "config" / "prompts.yaml")
    llm = settings.get("llm", {})
    local = llm.get("local", {})
    return ChatbotConfig(
        mode=settings.get("mode", "demo"),
        provider=llm.get("provider", "local"),
        backend=local.get("backend", "ollama"),
        model=local.get("model", "llama3.1:8b"),
        endpoint=local.get("endpoint", "http://localhost:11434"),
        system_prompt=prompts.get("chatbot_system", "You are a helpful assistant."),
    )


def load_friendly_prompt(project_root: Path) -> str:
    prompts = _load_yaml(project_root / "config" / "prompts.yaml")
    return prompts.get("friendly_system_prompt", "You are a helpful assistant.")


def list_local_models() -> list[str]:
    """Return locally available Ollama models or an empty list."""

    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, check=True
        )
    except FileNotFoundError:
        return []
    except subprocess.CalledProcessError:
        return []

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return []
    models = []
    for line in lines[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def _resolve_model(project_root: Path, model_override: str | None) -> tuple[str | None, str | None]:
    models = list_local_models()
    if model_override and model_override in models:
        return model_override, None
    if models:
        return models[0], None
    return None, "No local models found. Run: ollama pull <model>"


def _ollama_chat(
    *,
    endpoint: str,
    model: str,
    system_prompt: str,
    user_message: str,
    timeout: int = 15,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
    }
    try:
        response = requests.post(
            f"{endpoint}/api/chat", json=payload, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip() or "(No response.)"
    except Exception as exc:
        return (
            "Local LLM is unavailable. Ensure Ollama is running and the model is installed. "
            f"Details: {exc}"
        )


def _ollama_healthcheck(*, endpoint: str, model: str, timeout: int = 5) -> str | None:
    """Return an error message if Ollama or the model is unavailable."""

    try:
        response = requests.get(f"{endpoint}/api/tags", timeout=timeout)
        response.raise_for_status()
        data = response.json()
        models = {item.get("name") for item in data.get("models", [])}
        if model not in models:
            return (
                f"Ollama is running but model '{model}' is not installed. "
                f"Run: ollama pull {model}"
            )
        return None
    except Exception as exc:
        return f"Ollama health check failed: {exc}"


def friendly_chat_node(state: AgentState) -> dict:
    """Generate a friendly, direct response and return a message update."""

    project_root = Path(__file__).resolve().parents[2]
    user_message = ""
    messages = state.get("messages", [])
    if messages:
        last = messages[-1]
        if hasattr(last, "content"):
            user_message = last.content
        elif isinstance(last, tuple):
            user_message = last[1]
    system_prompt = load_friendly_prompt(project_root)
    prompt = f"{system_prompt}\n\nUser message: {user_message}\n"
    model, model_error = _resolve_model(project_root, state.get("model_name"))
    if model_error:
        response = model_error
    else:
        response = _ollama_chat(
            endpoint=load_chatbot_config(project_root).endpoint,
            model=model,
            system_prompt=system_prompt,
            user_message=user_message,
        )
    return {
        "messages": [AIMessage(content=response)],
        "final_answer": response,
        "last_model_output": response,
    }


def friendly_chat_response(
    *, project_root: Path, user_message: str, model_override: str | None = None
) -> str:
    """Return a direct friendly response without ReAct formatting."""

    model, model_error = _resolve_model(project_root, model_override)
    if model_error:
        return model_error
    system_prompt = load_friendly_prompt(project_root)
    return _ollama_chat(
        endpoint=load_chatbot_config(project_root).endpoint,
        model=model,
        system_prompt=system_prompt,
        user_message=user_message,
    )


def generate_reply(
    *,
    project_root: Path,
    user_message: str,
    agent_graph,
    model_override: str | None = None,
    mode_override: str | None = None,
) -> Tuple[str, str | None, list[str]]:
    config = load_chatbot_config(project_root)
    if config.provider != "local":
        return "API providers are disabled in the UI. Set llm.provider=local.", None, []
    if config.backend != "ollama":
        return "Unsupported local backend. Set llm.local.backend=ollama.", None, []
    if mode_override == "demo":
        reply = friendly_chat_response(
            project_root=project_root,
            user_message=user_message,
            model_override=model_override,
        )
        return reply, "demo", []
    model, model_error = _resolve_model(project_root, model_override)
    if model_error:
        return model_error, None, []
    health_error = _ollama_healthcheck(endpoint=config.endpoint, model=model)
    if health_error:
        return f"{health_error}", None, []
    response_state = agent_graph.invoke(
        {"messages": [HumanMessage(content=user_message)], "model_name": model}
    )
    final_answer = response_state.get("final_answer")
    if final_answer:
        return str(final_answer), response_state.get("intent"), response_state.get("thought_history", [])

    messages = response_state.get("messages", [])
    if not messages:
        print("⚠ Debug: No messages returned from graph.")
        return "No response generated.", response_state.get("intent"), response_state.get("thought_history", [])

    last = messages[-1]
    reply = last.content if hasattr(last, "content") else str(last)
    if reply == user_message:
        fallback = response_state.get("last_model_output")
        if fallback:
            reply = str(fallback)
    return reply, response_state.get("intent"), response_state.get("thought_history", [])


__all__ = ["friendly_chat_node", "generate_reply", "load_chatbot_config", "list_local_models"]
