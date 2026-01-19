from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from geopy.distance import geodesic

from src.models.report import AffectedSME
from src.tools.geo_utils import SMERegistryEntry, load_registry


def _distance_km(origin: Tuple[float, float], dest: Tuple[float, float]) -> float:
    return float(geodesic(origin, dest).km)


def get_smes_in_radius(
    *,
    registry_path: Path,
    center: Tuple[float, float],
    radius_km: float,
) -> tuple[list[AffectedSME], list[AffectedSME]]:
    """Return SMEs inside/outside the radius with distance annotations."""

    entries: Iterable[SMERegistryEntry] = load_registry(registry_path)
    affected: list[AffectedSME] = []
    safe: list[AffectedSME] = []

    for entry in entries:
        sme_coords = (entry.latitude, entry.longitude)
        distance_km = _distance_km(center, sme_coords)
        target = affected if distance_km <= radius_km else safe
        target.append(
            AffectedSME(
                sme_id=entry.sme_id,
                name=entry.name,
                county=entry.county,
                sector=entry.sector,
                latitude=entry.latitude,
                longitude=entry.longitude,
                distance_km=round(distance_km, 2),
            )
        )

    return affected, safe


def generate_risk_map(
    *,
    center: Tuple[float, float],
    radius_km: float,
    affected: Iterable[AffectedSME],
    safe: Iterable[AffectedSME],
    output_path: Path,
) -> None:
    """Generate an interactive HTML map for the risk zone."""

    try:
        import folium
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "folium is required to generate the risk map. "
            "Install it with: pip install folium"
        ) from exc

    map_view = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")

    pulse_css = """
    <style>
    .pulse-marker {
      width: 16px;
      height: 16px;
      background: rgba(220, 53, 69, 0.9);
      border-radius: 50%;
      position: relative;
      box-shadow: 0 0 0 6px rgba(220, 53, 69, 0.3);
    }
    .pulse-marker::after {
      content: "";
      position: absolute;
      left: 50%;
      top: 50%;
      width: 16px;
      height: 16px;
      margin-left: -8px;
      margin-top: -8px;
      background: rgba(220, 53, 69, 0.6);
      border-radius: 50%;
      animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
      0% { transform: scale(1); opacity: 0.9; }
      70% { transform: scale(2.6); opacity: 0; }
      100% { transform: scale(2.6); opacity: 0; }
    }
    </style>
    """
    map_view.get_root().header.add_child(folium.Element(pulse_css))

    folium.Marker(
        location=center,
        tooltip="Risk Epicenter",
        icon=folium.DivIcon(html='<div class="pulse-marker"></div>'),
    ).add_to(map_view)

    folium.Circle(
        location=center,
        radius=radius_km * 1000,
        color="#dc3545",
        weight=2,
        fill=True,
        fill_color="#dc3545",
        fill_opacity=0.15,
        tooltip=f"Impact radius: {radius_km:.1f} km",
    ).add_to(map_view)

    for sme in affected:
        if sme.latitude is None or sme.longitude is None:
            continue
        folium.Marker(
            location=(sme.latitude, sme.longitude),
            tooltip=f"{sme.name} (Affected)",
            popup=f"{sme.name} — {sme.sector} ({sme.distance_km} km)",
            icon=folium.Icon(color="red", icon="exclamation-sign"),
        ).add_to(map_view)

    for sme in safe:
        if sme.latitude is None or sme.longitude is None:
            continue
        folium.Marker(
            location=(sme.latitude, sme.longitude),
            tooltip=f"{sme.name} (Safe)",
            popup=f"{sme.name} — {sme.sector} ({sme.distance_km} km)",
            icon=folium.Icon(color="green", icon="ok-sign"),
        ).add_to(map_view)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    map_view.save(str(output_path))


__all__ = ["get_smes_in_radius", "generate_risk_map"]
