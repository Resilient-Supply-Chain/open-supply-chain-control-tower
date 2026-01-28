from __future__ import annotations

"""
Legacy pipeline entrypoint is commented out for the v2 workflow refactor.
See src/ui/app.py for the interactive chatbot UI.
"""

from src.ui.app import launch_app
from src.workflow.graph import build_react_graph


def main() -> None:
    react_graph = build_react_graph()
    launch_app(agent_graph=react_graph)


if __name__ == "__main__":
    main()

