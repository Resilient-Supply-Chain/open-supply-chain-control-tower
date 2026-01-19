from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from src.config import load_rag_settings
from src.agents.resilience_agent import _derive_priority, _render_markdown_alert
from src.models.rag_models import PolicyQueryResult
from src.models.report import ResilienceReport
from src.models.signal import RiskSignal
from src.tools.geo_engine import (
    analyze_supply_routes,
    generate_risk_map,
    get_smes_in_radius,
)
from src.tools.rag_engine import LegislationRAG, LegislationRAGConfig


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

    # --- 2. Initialize Legislation RAG over S.257 ---
    rag_settings = load_rag_settings()
    api_key_status = "present" if rag_settings.llama_cloud_api_key else "missing"
    print(f"ℹ RAG mode resolved to: {rag_settings.mode} (LLAMA_CLOUD_API_KEY {api_key_status})")
    preferred_pdf_path = project_root / "docs" / "S257_Act.pdf"
    fallback_pdf_path = (
        project_root / "data" / "static" / "legislation" / "BILLS-119s257es.pdf"
    )
    s257_pdf_path = preferred_pdf_path if preferred_pdf_path.exists() else fallback_pdf_path
    rag_index_dir = project_root / ".vector_store" / "s257_faiss"
    markdown_cache_path = project_root / "data" / "processed" / "S257_Act.md"
    rag_config = LegislationRAGConfig(
        pdf_path=s257_pdf_path,
        index_dir=rag_index_dir,
        rag_mode=rag_settings.mode,
        markdown_cache_path=markdown_cache_path,
        llama_cloud_api_key=rag_settings.llama_cloud_api_key,
    )
    rag_engine = LegislationRAG(rag_config)

    # Formulate a policy-aware query grounded in the current risk signal.
    policy_query = (
        "Under S.257 (Promoting Resilient Supply Chains Act of 2025), which "
        "sections or provisions are most relevant to a high-severity risk "
        f"event driven by '{risk_signal.primary_driver}' in the location "
        f"'{risk_signal.location}', particularly with respect to protecting "
        "small and medium-sized enterprises (SMEs) and regional supply-chain "
        "resilience?"
    )
    policy_result: PolicyQueryResult = rag_engine.query_policy(policy_query, k=4)
    print(f"✓ Retrieved {len(policy_result.snippets)} policy snippets from S.257")

    # --- 3. Load SME registry from static data ---
    registry_path = project_root / "data" / "static" / "sme_registry.json"

    # --- 4. Use geo engine to map epicenter to affected SMEs ---
    geo_center = risk_signal.geo_center
    affected_smes, safe_smes = get_smes_in_radius(
        registry_path=registry_path,
        center=(geo_center.lat, geo_center.lon),
        radius_km=geo_center.impact_radius_km,
    )
    print(
        f"✓ Found {len(affected_smes)} SMEs within {geo_center.impact_radius_km:.1f} km"
    )

    corridors_path = project_root / "data" / "static" / "highway_corridors.json"
    osrm_cache_path = project_root / "data" / "processed" / "osrm_cache.json"
    route_impacts = analyze_supply_routes(
        registry_path=registry_path,
        corridors_path=corridors_path,
        risk_center=(geo_center.lat, geo_center.lon),
        radius_km=geo_center.impact_radius_km,
        max_routes=3,
        max_miles=30.0,
        osrm_cache_path=osrm_cache_path,
    )

    # --- 5. Derive alert priority and render Markdown alert ---
    priority = _derive_priority(risk_signal.risk_score)

    policy_context = ""
    if policy_result.snippets:
        rag_mode_label = (
            "ADVANCED (LlamaParse Markdown)"
            if rag_settings.mode == "ADVANCED"
            else "LEGACY (Local PDF parsing)"
        )
        locator_label = "Section" if rag_settings.mode == "ADVANCED" else "Page"
        policy_lines: list[str] = [
            "",
            "### 📚 Relevant S.257 Policy Context",
            f"🔎 _RAG mode: **{rag_mode_label}**_",
            "The following passages are retrieved from "
            "**S.257 – Promoting Resilient Supply Chains Act of 2025**:",
        ]
        for snippet in policy_result.snippets:
            policy_lines.append(
                f"- 📄 **{locator_label} {snippet.page}** — {snippet.text.strip()}"
            )
        policy_context = "\n".join(policy_lines)

    geo_context = "\n".join(
        [
            "",
            "### 🗺️ Geospatial Risk Visualization",
            (
                f"SMEs within **{geo_center.impact_radius_km:.1f} km** of the "
                f"soil saturation epicenter at "
                f"({geo_center.lat:.4f}, {geo_center.lon:.4f}) "
                "are flagged for monitoring."
            ),
            "An interactive map has been generated at `outputs/risk_map.html`.",
        ]
    )

    interrupted_routes = [impact for impact in route_impacts if impact.interrupted]
    if interrupted_routes:
        logistics_lines = [
            "",
            "### 🚚 Logistics Infrastructure Impact",
        ]
        for impact in interrupted_routes:
            logistics_lines.append(
                (
                    f"- Route {impact.sme_id} ({impact.origin} ➔ {impact.destination}) "
                    "is severed at the Hwy 68 saturation segment, "
                    "stopping 100% of Peninsula deliveries."
                )
            )
        logistics_context = "\n".join(logistics_lines)
    else:
        logistics_context = ""

    markdown_alert = _render_markdown_alert(
        priority=priority,
        signal=risk_signal,
        affected_smes=affected_smes,
        policy_context=policy_context,
        geo_context=geo_context,
        logistics_context=logistics_context,
    )

    report = ResilienceReport(
        priority=priority,
        risk_signal=risk_signal,
        affected_smes=affected_smes,
        markdown_alert=markdown_alert,
    )

    # --- 6. Validation logic & outputs ---
    print("\n" + "=" * 80)
    print("SUPPLY CHAIN RESILIENCE ALERT")
    print("=" * 80 + "\n")
    print(report.markdown_alert)

    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    map_path = outputs_dir / "risk_map.html"
    try:
        generate_risk_map(
            center=(geo_center.lat, geo_center.lon),
            radius_km=geo_center.impact_radius_km,
            affected=affected_smes,
            safe=safe_smes,
            output_path=map_path,
            route_impacts=route_impacts,
            risk_center=(geo_center.lat, geo_center.lon),
            risk_radius_km=geo_center.impact_radius_km,
            label_colors=("#8B0000", "#006400"),
            segment_colors=("#FF6666", "#90EE90"),
        )
    except RuntimeError as exc:
        print(f"⚠ Map generation skipped: {exc}")

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
    # Load environment variables from .env (including HUGGINGFACEHUB_API_TOKEN,
    # ANTHROPIC_API_KEY, etc.) before any networked tools (RAG, PydanticAI) run.
    load_dotenv(override=True)
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

