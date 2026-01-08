from __future__ import annotations

import asyncio
from pathlib import Path

from src.agents.resilience_agent import _derive_priority, _render_markdown_alert
from src.models.report import ResilienceReport
from src.models.signal import RiskSignal
from src.tools.geo_utils import find_smes_by_location


async def run() -> None:
    """Execution entry point for the v0.0.1 AI Control Tower demo.

    This simulates a high-severity soil saturation event affecting Monterey
    County SMEs and generates a Markdown supply-chain alert consistent with
    S.257 and E.O. 14123 priorities.
    """

    # --- 1. Simulate inbound RiskSignal (validated by Pydantic) ---
    risk_signal = RiskSignal(
        risk_score=0.95,
        location="Monterey_Hwy68",
        primary_driver="Soil_Saturation_Critical",
        estimated_impact="$15M_Day",
    )

    project_root = Path(__file__).parent
    registry_path = project_root / "data" / "sme_registry.json"

    # --- 2. Use geo tool to map location to affected SMEs ---
    # For v0.0.1 we map the broader Monterey geography (county-level).
    affected_smes = find_smes_by_location(
        registry_path=registry_path, location="Monterey"
    )

    # --- 3. Derive alert priority and render Markdown alert ---
    priority = _derive_priority(risk_signal.risk_score)
    markdown_alert = _render_markdown_alert(
        priority=priority,
        signal=risk_signal,
        affected_smes=affected_smes,
    )

    report = ResilienceReport(
        priority=priority,
        risk_signal=risk_signal,
        affected_smes=affected_smes,
        markdown_alert=markdown_alert,
    )

    # --- 4. Validation logic & outputs ---
    print(report.markdown_alert)

    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = outputs_dir / "monterey_risk_report_v001.md"

    if risk_signal.risk_score > 0.9:
        # Persist only high-priority alerts for v0.0.1
        output_path.write_text(report.markdown_alert, encoding="utf-8")
    else:
        # Below threshold: treat as logged event without high-priority alert file.
        print(
            "Risk score below 0.9; event logged but no High Priority alert persisted."
        )


if __name__ == "__main__":
    asyncio.run(run())

