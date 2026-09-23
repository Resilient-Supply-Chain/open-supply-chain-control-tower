from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

MISSING_SENTINELS = {"", "na", "n/a", "null", "none", "nan"}


def _is_missing(value: str) -> bool:
    return value.strip().lower() in MISSING_SENTINELS


def _flatten_keys(data: object, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            keys.extend(_flatten_keys(value, next_prefix))
    elif isinstance(data, list):
        if data:
            keys.extend(_flatten_keys(data[0], prefix))
        else:
            if prefix:
                keys.append(prefix)
    else:
        if prefix:
            keys.append(prefix)
    return keys


def check_csv_missing_values(csv_path: Path, *, max_rows: int | None = None) -> str:
    """Check CSV for missing values and return a concise summary."""

    if not csv_path.exists():
        return f"Data checker error: file not found at {csv_path}"

    missing_counts: Dict[str, int] = {}
    total_rows = 0
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return "Data checker error: CSV header is missing."
        for row in reader:
            total_rows += 1
            for key, value in row.items():
                if _is_missing(value or ""):
                    missing_counts[key] = missing_counts.get(key, 0) + 1
            if max_rows and total_rows >= max_rows:
                break

    if total_rows == 0:
        return "Data checker: no data rows found."

    if not missing_counts:
        return f"Data checker: no missing values detected across {total_rows} rows."

    lines: List[str] = [
        f"Data checker summary for {csv_path.name}:",
        f"- Rows scanned: {total_rows}",
        "- Missing values by column:",
    ]
    for column, count in sorted(missing_counts.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"  - {column}: {count}")
    return "\n".join(lines)


def check_csv_against_template(
    *, csv_path: Path, template_path: Path, max_rows: int | None = 500
) -> str:
    """Compare CSV columns to a JSON template and report missing fields."""

    if not template_path.exists():
        return f"Data checker error: template not found at {template_path}"
    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"Data checker error: failed to parse template JSON: {exc}"

    required_fields = set(_flatten_keys(template))
    if not required_fields:
        return "Data checker error: template has no fields."

    if not csv_path.exists():
        return f"Data checker error: file not found at {csv_path}"

    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return "Data checker error: CSV header is missing."
        csv_fields = set(reader.fieldnames)

        missing_columns = sorted(required_fields - csv_fields)
        summary = [f"Template coverage check for {csv_path.name}:"]
        summary.append(f"- Required fields (template): {len(required_fields)}")
        summary.append(f"- CSV columns: {len(csv_fields)}")
        if missing_columns:
            summary.append(f"- Missing required fields: {len(missing_columns)}")
            summary.extend([f"  - {field}" for field in missing_columns[:25]])
            if len(missing_columns) > 25:
                summary.append(f"  ... (+{len(missing_columns) - 25} more)")
        else:
            summary.append("- Missing required fields: 0")

    missing_values_summary = check_csv_missing_values(csv_path, max_rows=max_rows)
    return "\n".join(summary + ["", missing_values_summary])


def check_provider_dataset(
    *,
    csv_path: Path,
    template_path: Path,
    evidence_dir: Path,
    max_rows: int | None = 500,
) -> str:
    """Validate provider CSV against template with field mapping and evidence checks."""

    if not csv_path.exists():
        return f"Data checker error: file not found at {csv_path}"
    if not template_path.exists():
        return f"Data checker error: template not found at {template_path}"

    template = json.loads(template_path.read_text(encoding="utf-8"))
    required_fields = set(_flatten_keys(template))

    field_map = {
        "timestamp": "date",
        "location.county": "county_name",
        "risk_score": "predicted_risk_score",
        "risk_score_max": None,  # fixed value = 100
    }

    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return "Data checker error: CSV header is missing."
        csv_fields = set(reader.fieldnames)

    mapped_missing = []
    for required in sorted(required_fields):
        if required in field_map:
            mapped = field_map[required]
            if mapped and mapped not in csv_fields:
                mapped_missing.append(f"{required} -> {mapped}")
            continue
        if required not in csv_fields:
            mapped_missing.append(required)

    evidence_files = sorted(
        path.stem
        for path in evidence_dir.glob("*.csv")
        if path.is_file()
    ) if evidence_dir.exists() else []

    template_metrics = [
        item.get("metric_name")
        for item in template.get("evidence_bundle", [])
        if isinstance(item, dict) and item.get("metric_name")
    ]
    missing_metrics = sorted(
        metric for metric in template_metrics if metric not in evidence_files
    )

    lines = [
        f"Provider dataset check: {csv_path.name}",
        f"- CSV columns: {len(csv_fields)}",
    ]
    if mapped_missing:
        lines.append(f"- Missing required fields: {len(mapped_missing)}")
        lines.extend([f"  - {field}" for field in mapped_missing[:25]])
        if len(mapped_missing) > 25:
            lines.append(f"  ... (+{len(mapped_missing) - 25} more)")
    else:
        lines.append("- Missing required fields: 0")

    lines.append(
        f"- Evidence files found: {len(evidence_files)}"
        + (f" ({', '.join(evidence_files)})" if evidence_files else "")
    )
    if missing_metrics:
        lines.append(f"- Missing evidence metrics: {len(missing_metrics)}")
        lines.extend([f"  - {metric}" for metric in missing_metrics])
    else:
        lines.append("- Missing evidence metrics: 0")

    missing_values_summary = check_csv_missing_values(csv_path, max_rows=max_rows)
    return "\n".join(lines + ["", missing_values_summary])


__all__ = [
    "check_csv_against_template",
    "check_csv_missing_values",
    "check_provider_dataset",
]

