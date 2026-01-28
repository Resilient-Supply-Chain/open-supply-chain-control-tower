from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
import requests
import subprocess

from src.state import AgentState


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


def _format_react_output(state: AgentState | dict) -> str:
    if isinstance(state, dict):
        thought_output = state.get("last_model_output")
        final_answer = state.get("final_answer")
    else:
        thought_output = state.last_model_output
        final_answer = state.final_answer

    if thought_output and final_answer:
        return f"{thought_output}\n\nFinal Answer: {final_answer}"
    if thought_output:
        return thought_output
    if final_answer:
        return str(final_answer)
    return "No response generated."


def generate_reply(
    *,
    project_root: Path,
    user_message: str,
    agent_graph,
    model_override: str | None = None,
) -> str:
    config = load_chatbot_config(project_root)
    if config.provider != "local":
        return "API providers are disabled in the UI. Set llm.provider=local."
    if config.backend != "ollama":
        return "Unsupported local backend. Set llm.local.backend=ollama."
    model = model_override or config.model
    health_error = _ollama_healthcheck(endpoint=config.endpoint, model=model)
    if health_error:
        return f"{health_error}"
    response_state = agent_graph.invoke({"messages": [("user", user_message)]})
    return _format_react_output(response_state)


__all__ = ["generate_reply", "load_chatbot_config", "list_local_models"]
