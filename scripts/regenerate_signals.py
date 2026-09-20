"""Regenerate data/input/signals/*.json from data/output/data_series.json.

Produces a snapshot of all counties on a single TARGET_DATE. Derives risk_score,
primary_driver, estimated_impact, and recommendation deterministically from
county id + level. Preserves geo_center from the existing signal file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIES_PATH = ROOT / "data" / "output" / "data_series.json"
SIGNALS_DIR = ROOT / "data" / "input" / "signals"
TARGET_DATE = "2023-01-07"

LEVEL_RANK = {"low": 0, "moderate": 1, "high": 2}

HIGH_DRIVERS = [
    "Downed_Trees_on_Lines",
    "Atmospheric_River_Winds",
    "Flood_Damaged_Substation",
    "Transmission_Line_Down",
    "Saturated_Soil_Pole_Failure",
]
MOD_DRIVERS = [
    "Gusty_Winds",
    "Vegetation_Contact",
    "Localized_Flooding",
    "Distribution_Line_Fault",
    "Mudslide_Risk",
]
LOW_DRIVERS = [
    "Scheduled_Maintenance",
    "Isolated_Feeder_Fault",
    "Routine_Inspection",
]

HIGH_RECS = [
    "Dispatch crews to clear fallen trees",
    "Isolate flooded substations; reroute load",
    "Activate mutual-aid from neighboring utilities",
]
MOD_RECS = [
    "Pre-position tree-trimming crews",
    "Increase line patrols ahead of next cell",
    "Harden vegetation management zones",
]
LOW_RECS = [
    "Continue routine monitoring",
    "Schedule preventive maintenance",
    "No action required",
]

# Short phrase used on cards instead of a dollar figure.
IMPACT_BY_LEVEL = {
    "high": "Widespread customer outages",
    "moderate": "Scattered outages possible",
    "low": "Nominal service",
}
SCORE_BY_LEVEL = {"high": 0.85, "moderate": 0.50, "low": 0.15}


# Approximate county-seat / centroid coordinates for CA counties.
COUNTY_GEO: dict[str, dict] = {
    "alameda": {"lat": 37.6017, "lon": -121.7195, "impact_radius_km": 15},
    "alpine": {"lat": 38.5974, "lon": -119.8207, "impact_radius_km": 15},
    "amador": {"lat": 38.4464, "lon": -120.6535, "impact_radius_km": 15},
    "butte": {"lat": 39.6254, "lon": -121.5370, "impact_radius_km": 15},
    "calaveras": {"lat": 38.1960, "lon": -120.5540, "impact_radius_km": 15},
    "colusa": {"lat": 39.1041, "lon": -122.2378, "impact_radius_km": 15},
    "contra_costa": {"lat": 37.9194, "lon": -121.9517, "impact_radius_km": 15},
    "del_norte": {"lat": 41.7405, "lon": -123.8956, "impact_radius_km": 15},
    "el_dorado": {"lat": 38.7787, "lon": -120.5239, "impact_radius_km": 15},
    "fresno": {"lat": 36.7378, "lon": -119.7871, "impact_radius_km": 15},
    "glenn": {"lat": 39.5982, "lon": -122.3928, "impact_radius_km": 15},
    "humboldt": {"lat": 40.7450, "lon": -123.8695, "impact_radius_km": 15},
    "imperial": {"lat": 33.0389, "lon": -115.3654, "impact_radius_km": 15},
    "inyo": {"lat": 36.5111, "lon": -117.4107, "impact_radius_km": 15},
    "kern": {"lat": 35.3433, "lon": -118.7276, "impact_radius_km": 15},
    "kings": {"lat": 36.0753, "lon": -119.8155, "impact_radius_km": 15},
    "lake": {"lat": 39.0994, "lon": -122.7533, "impact_radius_km": 15},
    "lassen": {"lat": 40.6741, "lon": -120.5945, "impact_radius_km": 15},
    "los_angeles": {"lat": 34.0522, "lon": -118.2437, "impact_radius_km": 20},
    "madera": {"lat": 37.2100, "lon": -119.7659, "impact_radius_km": 15},
    "marin": {"lat": 38.0834, "lon": -122.7633, "impact_radius_km": 15},
    "mariposa": {"lat": 37.5706, "lon": -119.9138, "impact_radius_km": 15},
    "mendocino": {"lat": 39.4457, "lon": -123.3425, "impact_radius_km": 15},
    "merced": {"lat": 37.1920, "lon": -120.7120, "impact_radius_km": 15},
    "modoc": {"lat": 41.5892, "lon": -120.7233, "impact_radius_km": 15},
    "mono": {"lat": 37.9219, "lon": -118.8987, "impact_radius_km": 15},
    "monterey": {"lat": 36.2404, "lon": -121.3100, "impact_radius_km": 15},
    "napa": {"lat": 38.5025, "lon": -122.2654, "impact_radius_km": 15},
    "nevada": {"lat": 39.3012, "lon": -120.7690, "impact_radius_km": 15},
    "orange": {"lat": 33.7175, "lon": -117.8311, "impact_radius_km": 15},
    "placer": {"lat": 39.0630, "lon": -120.7177, "impact_radius_km": 15},
    "plumas": {"lat": 40.0042, "lon": -120.8039, "impact_radius_km": 15},
    "riverside": {"lat": 33.7175, "lon": -116.2023, "impact_radius_km": 15},
    "sacramento": {"lat": 38.4747, "lon": -121.3542, "impact_radius_km": 15},
    "san_benito": {"lat": 36.6062, "lon": -121.0750, "impact_radius_km": 15},
    "san_bernardino": {"lat": 34.9592, "lon": -116.4194, "impact_radius_km": 15},
    "san_diego": {"lat": 32.7157, "lon": -117.1611, "impact_radius_km": 15},
    "san_francisco": {"lat": 37.7749, "lon": -122.4194, "impact_radius_km": 10},
    "san_joaquin": {"lat": 37.9351, "lon": -121.2719, "impact_radius_km": 15},
    "san_luis_obispo": {"lat": 35.3850, "lon": -120.4472, "impact_radius_km": 15},
    "san_mateo": {"lat": 37.4337, "lon": -122.4014, "impact_radius_km": 15},
    "santa_barbara": {"lat": 34.5361, "lon": -120.0386, "impact_radius_km": 15},
    "santa_clara": {"lat": 37.2333, "lon": -121.6907, "impact_radius_km": 15},
    "santa_cruz": {"lat": 37.0454, "lon": -121.9500, "impact_radius_km": 15},
    "shasta": {"lat": 40.7909, "lon": -121.8474, "impact_radius_km": 15},
    "sierra": {"lat": 39.5780, "lon": -120.5148, "impact_radius_km": 15},
    "siskiyou": {"lat": 41.5929, "lon": -122.5406, "impact_radius_km": 15},
    "solano": {"lat": 38.2676, "lon": -121.9401, "impact_radius_km": 15},
    "sonoma": {"lat": 38.5780, "lon": -122.9888, "impact_radius_km": 15},
    "stanislaus": {"lat": 37.5591, "lon": -120.9977, "impact_radius_km": 15},
    "sutter": {"lat": 39.0346, "lon": -121.6948, "impact_radius_km": 15},
    "tehama": {"lat": 40.1257, "lon": -122.2344, "impact_radius_km": 15},
    "trinity": {"lat": 40.6502, "lon": -123.1102, "impact_radius_km": 15},
    "tulare": {"lat": 36.2077, "lon": -118.7815, "impact_radius_km": 15},
    "tuolumne": {"lat": 38.0297, "lon": -119.9543, "impact_radius_km": 15},
    "ventura": {"lat": 34.3705, "lon": -119.1391, "impact_radius_km": 15},
    "yolo": {"lat": 38.7646, "lon": -121.9018, "impact_radius_km": 15},
    "yuba": {"lat": 39.2686, "lon": -121.3528, "impact_radius_km": 15},
}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def pick(items: list[str], seed: int) -> str:
    return items[seed % len(items)]


def load_geo_defaults() -> dict[str, dict]:
    """Deprecated; kept as no-op for backward compat. Use COUNTY_GEO instead."""
    return {}


def snapshot_for_date(series: dict, date: str) -> dict[str, tuple[str, str, str]]:
    """Return {county_name: (date, riskLevel, riskType)} for the target date."""
    if date not in series:
        raise SystemExit(f"TARGET_DATE {date} not in data_series.json")
    return {
        c["name"]: (date, c.get("riskLevel", "low"), c.get("riskType", "No Risk"))
        for c in series[date]
    }


def main() -> None:
    series = json.loads(SERIES_PATH.read_text())
    peaks = snapshot_for_date(series, TARGET_DATE)

    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for name, (date, level, _rtype) in peaks.items():
        seed = sum(ord(ch) for ch in name)
        if level == "high":
            driver = pick(HIGH_DRIVERS, seed)
            rec = pick(HIGH_RECS, seed)
        elif level == "moderate":
            driver = pick(MOD_DRIVERS, seed)
            rec = pick(MOD_RECS, seed)
        else:
            driver = pick(LOW_DRIVERS, seed)
            rec = pick(LOW_RECS, seed)

        # small deterministic jitter so scores aren't identical
        jitter = ((seed % 9) - 4) / 100.0  # -0.04 .. +0.04
        score = round(SCORE_BY_LEVEL[level] + jitter, 2)
        hour = seed % 24
        timestamp = f"{date}T{hour:02d}:00:00Z"

        geo = COUNTY_GEO.get(slug(name), {"lat": 37.0, "lon": -120.0, "impact_radius_km": 15})

        signal = {
            "risk_score": score,
            "location": f"{name.replace(' ', '_')}_County",
            "primary_driver": driver,
            "estimated_impact": IMPACT_BY_LEVEL[level],
            "recommendation": rec,
            "timestamp": timestamp,
            "geo_center": geo,
        }
        out_path = SIGNALS_DIR / f"{slug(name)}_risk_event.json"
        out_path.write_text(json.dumps(signal, indent=2) + "\n")
        written += 1

    print(f"Regenerated {written} signal files for {TARGET_DATE} in {SIGNALS_DIR}")


if __name__ == "__main__":
    main()
