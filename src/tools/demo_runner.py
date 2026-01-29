from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.tools.data_bridge import run_conversion


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_demo_presentation(*, project_root: str | Path | None = None) -> Dict[str, Any]:
    """Run the demo data conversion pipeline and return the dashboard URL.

    Args:
        project_root: Absolute path to the project root directory.

    Returns:
        A dict with conversion details and the demo dashboard URL.
    """

    root = Path(project_root) if project_root else _default_project_root()
    source_file = (
        root
        / "data"
        / "input"
        / "registered_provider"
        / "OSCCT_risk_model"
        / "power_outage"
        / "dec2022_mar2023"
        / "OSCCT_risk_predict_model.csv"
    )
    dest_file = root / "data" / "output" / "data_series.json"
    result = run_conversion(source_file=source_file, dest_file=dest_file)
    return {
        "status": "ok",
        "message": result,
        "output_path": str(dest_file),
        "demo_url": "https://oact-sepia.vercel.app/",
    }


def react_run_demo(*, project_root: str | Path | None = None) -> Dict[str, Any]:
    """Alias for running the demo conversion from ReAct."""

    return run_demo_presentation(project_root=project_root)


__all__ = ["react_run_demo", "run_demo_presentation"]
