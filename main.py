from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from src.agents.resilience_agent import _derive_priority, _render_markdown_alert
from src.models.report import ResilienceReport
from src.models.signal import RiskSignal
from src.tools.geo_utils import find_smes_by_location


def load_risk_signal(signal_path: Path) -> RiskSignal:
    """Load and validate a RiskSignal from a JSON file.

    Args:
        signal_path: Path to the JSON file containing risk signal data.

    Returns:
        Validated RiskSignal instance.

    Raises:
        FileNotFoundError: If the signal file does not exist.
        ValueError: If the JSON cannot be parsed or validated.
    """
    if not signal_path.exists():
        raise FileNotFoundError(f"Risk signal file not found: {signal_path}")

    try:
        # Use Pydantic's model_validate_json for type-safe parsing
        json_content = signal_path.read_text(encoding="utf-8")
        return RiskSignal.model_validate_json(json_content)
    except Exception as e:
        raise ValueError(f"Failed to parse risk signal from {signal_path}: {e}") from e


async def run(signal_file: Path | None = None) -> None:
    """Execution entry point for the v0.0.1 AI Control Tower demo.

    Processes a risk signal from a JSON file and generates a Markdown
    supply-chain alert consistent with S.257 and E.O. 14123 priorities.

    Args:
        signal_file: Optional path to the risk signal JSON file.
                    Defaults to data/signals/monterey_risk_event.json
    """

    project_root = Path(__file__).parent

    # --- 1. Load RiskSignal from JSON file (validated by Pydantic) ---
    if signal_file is None:
        signal_file = project_root / "data" / "signals" / "monterey_risk_event.json"

    risk_signal = load_risk_signal(signal_file)
    print(f"✓ Loaded risk signal from: {signal_file}")

    # --- 2. Load SME registry from static data ---
    registry_path = project_root / "data" / "static" / "sme_registry.json"

    # --- 3. Use geo tool to map location to affected SMEs ---
    # For v0.0.1 we map the broader Monterey geography (county-level).
    # Extract location token for matching (e.g., "Monterey" from "Monterey_Hwy68")
    location_token = risk_signal.location.split("_")[0] if "_" in risk_signal.location else risk_signal.location
    affected_smes = find_smes_by_location(
        registry_path=registry_path, location=location_token
    )
    print(f"✓ Found {len(affected_smes)} potentially affected SMEs")

    # --- 4. Derive alert priority and render Markdown alert ---
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

    # --- 5. Validation logic & outputs ---
    print("\n" + "=" * 80)
    print("SUPPLY CHAIN RESILIENCE ALERT")
    print("=" * 80 + "\n")
    print(report.markdown_alert)

    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename from signal file name
    signal_stem = signal_file.stem
    output_path = outputs_dir / f"{signal_stem}_report_v001.md"

    if risk_signal.risk_score > 0.9:
        # Persist only high-priority alerts for v0.0.1
        output_path.write_text(report.markdown_alert, encoding="utf-8")
        print(f"\n✓ High-priority alert saved to: {output_path}")
    else:
        # Below threshold: treat as logged event without high-priority alert file.
        print(
            "\n⚠ Risk score below 0.9; event logged but no High Priority alert persisted."
        )


def main() -> None:
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="AI Control Tower for U.S. Supply-Chain Resilience (v0.0.1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python main.py\n"
            "  python main.py --signal data/signals/monterey_risk_event.json\n"
        ),
    )
    parser.add_argument(
        "--signal",
        type=Path,
        default=None,
        help="Path to risk signal JSON file (default: data/signals/monterey_risk_event.json)",
    )

    args = parser.parse_args()
    try:
        asyncio.run(run(signal_file=args.signal))
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()

