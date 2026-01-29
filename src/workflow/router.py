from __future__ import annotations

from pathlib import Path
from typing import Literal

import requests
import yaml

from src.state import AgentState


def _load_llm_settings(project_root: Path) -> dict:
    settings_path = project_root / "config" / "settings.yaml"
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    return settings.get("llm", {})


def _call_local_llm(prompt: str, project_root: Path, *, model: str | None = None) -> str:
    llm = _load_llm_settings(project_root)
    local = llm.get("local", {})
    endpoint = local.get("endpoint", "http://localhost:11434")
    model = model or local.get("model", "llama3.1:8b")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(f"{endpoint}/api/generate", json=payload, timeout=10)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent as chat or task using the LLM."""

    project_root = Path(__file__).resolve().parents[2]
    messages = state.get("messages", [])
    user_message = ""
    if messages:
        last = messages[-1]
        if hasattr(last, "content"):
            user_message = last.content
        elif isinstance(last, tuple):
            user_message = last[1]
    print("🔎 Node: classify_intent")
    prompt = (
        "Classify the user intent as one of: chat or task.\n"
        "chat = greeting, small talk, or general conversation.\n"
        "task = requests that require tools or actions.\n"
        "Return only one word: chat or task.\n\n"
        f"User message: {user_message}\n"
    )
    result = _call_local_llm(prompt, project_root, model=state.get("model_name"))
    normalized = result.strip().lower().split()[0] if result.strip() else ""
    intent: Literal["chat", "task"] = "task"
    if normalized == "chat" or "chat" in normalized:
        intent = "chat"
    state["intent"] = intent
    return state


__all__ = ["classify_intent"]

