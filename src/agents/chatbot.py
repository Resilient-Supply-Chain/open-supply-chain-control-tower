from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
import requests
import subprocess

import re
from src.agents.refactor_agent import run_demo_conversion
from src.tools.ses_mailer import broadcast_risk_alert_ses


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
    timeout: int = 120,
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


def generate_reply(
    *, project_root: Path, user_message: str, model_override: str | None = None
) -> str:
    # Pattern match for "today is YYYY-MM-DD" (e.g., "today is 2023-01-04, check risks")
    date_match = re.search(r"today is (\d{4}-\d{2}-\d{2})", user_message.lower())
    if date_match:
        target_date = date_match.group(1)
        # In a real scenario, these keys would come from the user or env vars
        # For now, we call it without keys, relying on env vars or error handling
        return broadcast_risk_alert_ses(target_date=target_date)

    if "demo" in user_message.lower():
        conversion_result = run_demo_conversion(project_root=project_root)
        return "\n".join(
            [
                "### Demo Workflow",
                "1. Locate relevant provider data based on the prompt.",
                "2. Convert provider data into UI-ready JSON.",
                "3. Send converted data to the UI layer.",
                f"   - {conversion_result}",
                "4. Open the dashboard:",
                "   - https://oact-sepia.vercel.app/",
            ]
        )
    config = load_chatbot_config(project_root)
    if config.provider != "local":
        return "API providers are disabled in the UI. Set llm.provider=local."
    if config.backend != "ollama":
        return "Unsupported local backend. Set llm.local.backend=ollama."
    model = model_override or config.model
    health_error = _ollama_healthcheck(endpoint=config.endpoint, model=model)
    if health_error:
        return f"{health_error}"
    return _ollama_chat(
        endpoint=config.endpoint,
        model=model,
        system_prompt=config.system_prompt,
        user_message=user_message,
    )


__all__ = ["generate_reply", "load_chatbot_config", "list_local_models"]
