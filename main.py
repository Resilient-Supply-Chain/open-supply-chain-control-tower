from __future__ import annotations

"""
Legacy pipeline entrypoint is commented out for the v2 workflow refactor.
See src/ui/app.py for the interactive chatbot UI.
"""

from src.ui.app import launch_app


def main() -> None:
    launch_app()


if __name__ == "__main__":
    main()

