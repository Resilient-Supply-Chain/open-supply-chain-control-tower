from __future__ import annotations

"""
Legacy pipeline entrypoint is commented out for the v2 workflow refactor.
See src/ui/app.py for the interactive chatbot UI.

Run this from the repository root (`python apps/agent/main.py`): the agent
writes to data/ at the repo root, and several call sites resolve that path
against the current working directory.
"""

import sys
from pathlib import Path

# Put apps/agent/ on sys.path so `src.*` and `config.*` resolve no matter which
# directory the process was started from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ui.app import launch_app  # noqa: E402


def main() -> None:
    launch_app()


if __name__ == "__main__":
    main()

