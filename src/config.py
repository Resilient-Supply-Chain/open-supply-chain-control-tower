from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

RagMode = Literal["LEGACY", "ADVANCED"]


@dataclass(frozen=True)
class RAGSettings:
    """Runtime configuration for the S.257 RAG pipeline."""

    mode: RagMode
    llama_cloud_api_key: str | None


def load_rag_settings() -> RAGSettings:
    """Load RAG settings from environment variables with safe fallbacks."""

    raw_mode = (os.getenv("RAG_MODE") or "LEGACY").upper()
    print(f"ℹ RAG_MODE env raw value: {os.getenv('RAG_MODE')!r}")
    mode: RagMode = "ADVANCED" if raw_mode == "ADVANCED" else "LEGACY"
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")

    if mode == "ADVANCED" and not api_key:
        print(
            "⚠ RAG_MODE=ADVANCED but LLAMA_CLOUD_API_KEY is missing. "
            "Falling back to LEGACY parsing."
        )
        mode = "LEGACY"

    return RAGSettings(mode=mode, llama_cloud_api_key=api_key)


__all__ = ["RagMode", "RAGSettings", "load_rag_settings"]
