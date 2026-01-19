from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Tuple

import math
import requests

from geopy.distance import geodesic

from src.models.report import AffectedSME
from src.tools.geo_utils import DeliveryRoute, SMERegistryEntry, load_registry


def _distance_km(origin: Tuple[float, float], dest: Tuple[float, float]) -> float:
    return float(geodesic(origin, dest).km)


def _distance_miles(origin: Tuple[float, float], dest: Tuple[float, float]) -> float:
    return _distance_km(origin, dest) * 0.621371


def _closest_point_on_segment(
    start: Tuple[float, float],
    end: Tuple[float, float],
    point: Tuple[float, float],
) -> Tuple[float, float]:
    """Return closest point on line segment in lat/lon degree space."""

    (x1, y1), (x2, y2) = start, end
    px, py = point
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return start
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return (x1 + t * dx, y1 + t * dy)


@dataclass(frozen=True)
class RouteImpact:
    sme_id: str
    name: str
    origin: str
    destination: str
    interrupted: bool
    intersection_point: Tuple[float, float] | None
    waypoints: list[Tuple[float, float]]


def load_highway_corridors(corridors_path: Path) -> dict[str, list[Tuple[float, float]]]:
    raw = json.loads(corridors_path.read_text(encoding="utf-8"))
    corridors: dict[str, list[Tuple[float, float]]] = {}
    for name, points in raw.items():
        corridors[name] = [(float(lat), float(lon)) for lat, lon in points]
    return corridors


def _load_osrm_cache(cache_path: Path) -> dict[str, list[Tuple[float, float]]]:
    if not cache_path.exists():
        return {}
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        return {k: [(p[0], p[1]) for p in v] for k, v in raw.items()}
    except Exception:
        return {}


def _save_osrm_cache(cache_path: Path, cache: dict[str, list[Tuple[float, float]]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: [[p[0], p[1]] for p in v] for k, v in cache.items()}
    cache_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


def _cache_key(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> str:
    return f"{start_coords[0]:.5f},{start_coords[1]:.5f}|{end_coords[0]:.5f},{end_coords[1]:.5f}"


def get_real_road_path(
    start_coords: Tuple[float, float],
    end_coords: Tuple[float, float],
    *,
    cache: dict[str, list[Tuple[float, float]]] | None = None,
    cache_path: Path | None = None,
) -> list[Tuple[float, float]]:
    """Return dense road path between two points using OSRM."""

    cache = cache or {}
    key = _cache_key(start_coords, end_coords)
    if key in cache:
        return cache[key]

    print(f"⏳ OSRM route request: {start_coords} -> {end_coords}")
    lon1, lat1 = start_coords[1], start_coords[0]
    lon2, lat2 = end_coords[1], end_coords[0]
    url = (
        "http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )
    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        payload = response.json()
        coords = payload["routes"][0]["geometry"]["coordinates"]
        path = [(lat, lon) for lon, lat in coords]
        cache[key] = path
        if cache_path:
            _save_osrm_cache(cache_path, cache)
        print(f"✓ OSRM route received: {len(path)} points")
        return path
    except Exception:
        # Fallback to straight line if OSRM fails.
        fallback = [start_coords, end_coords]
        cache[key] = fallback
        if cache_path:
            _save_osrm_cache(cache_path, cache)
        print("⚠ OSRM route failed; using straight-line fallback")
        return fallback


def _route_length_miles(route: list[Tuple[float, float]]) -> float:
    total = 0.0
    for idx in range(len(route) - 1):
        total += _distance_miles(route[idx], route[idx + 1])
    return total


def _trim_route_by_miles(
    route: list[Tuple[float, float]], max_miles: float
) -> list[Tuple[float, float]]:
    if len(route) < 2:
        return route
    total = 0.0
    trimmed = [route[0]]
    for idx in range(len(route) - 1):
        segment = _distance_miles(route[idx], route[idx + 1])
        if total + segment > max_miles:
            trimmed.append(route[idx + 1])
            return trimmed
        total += segment
        trimmed.append(route[idx + 1])
    return trimmed


def _downsample_route(
    route: list[Tuple[float, float]], max_points: int = 200
) -> list[Tuple[float, float]]:
    if len(route) <= max_points:
        return route
    step = max(1, len(route) // max_points)
    sampled = route[::step]
    if sampled[-1] != route[-1]:
        sampled.append(route[-1])
    return sampled


def _nearest_point_on_corridor(
    corridor: list[Tuple[float, float]],
    point: Tuple[float, float],
) -> tuple[Tuple[float, float], int]:
    closest = corridor[0]
    closest_index = 0
    closest_distance = math.inf
    for idx in range(len(corridor) - 1):
        candidate = _closest_point_on_segment(corridor[idx], corridor[idx + 1], point)
        distance_km = _distance_km(point, candidate)
        if distance_km < closest_distance:
            closest_distance = distance_km
            closest = candidate
            closest_index = idx + 1
    return closest, closest_index


def generate_realistic_routes(
    *,
    sme_coords: Tuple[float, float],
    corridors: dict[str, list[Tuple[float, float]]],
    max_routes: int = 3,
    max_miles: float = 30.0,
    cache_path: Path | None = None,
) -> list[tuple[str, list[Tuple[float, float]]]]:
    cache = _load_osrm_cache(cache_path) if cache_path else {}
    corridor_scores: list[tuple[str, float, int, Tuple[float, float]]] = []
    for name, points in corridors.items():
        nearest_point, index = _nearest_point_on_corridor(points, sme_coords)
        corridor_scores.append((name, _distance_miles(sme_coords, nearest_point), index, nearest_point))

    corridor_scores.sort(key=lambda item: item[1])
    routes: list[tuple[str, list[Tuple[float, float]]]] = []

    for name, _, start_index, nearest_point in corridor_scores[:max_routes]:
        corridor = corridors[name]
        tail = corridor[start_index : start_index + 2]
        raw_route = [sme_coords, nearest_point] + tail
        dense_route: list[Tuple[float, float]] = []
        for idx in range(len(raw_route) - 1):
            segment = get_real_road_path(
                raw_route[idx],
                raw_route[idx + 1],
                cache=cache,
                cache_path=cache_path,
            )
            if dense_route and segment:
                dense_route.extend(segment[1:])
            else:
                dense_route.extend(segment)
        dense_route = _trim_route_by_miles(dense_route, max_miles)
        dense_route = _downsample_route(dense_route, max_points=200)
        if len(dense_route) >= 2:
            routes.append((name, dense_route))

    return routes


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


def is_route_interrupted(
    *,
    route: DeliveryRoute,
    risk_center: Tuple[float, float],
    radius_km: float,
) -> Tuple[bool, Tuple[float, float] | None]:
    """Check if any segment passes within the risk radius."""

    waypoints = [(wp.lat, wp.lon) for wp in route.waypoints]
    closest_point: Tuple[float, float] | None = None
    closest_distance = math.inf
    for idx in range(len(waypoints) - 1):
        start = waypoints[idx]
        end = waypoints[idx + 1]
        candidate = _closest_point_on_segment(start, end, risk_center)
        distance_km = _distance_km(risk_center, candidate)
        if distance_km < closest_distance:
            closest_distance = distance_km
            closest_point = candidate
        if distance_km <= radius_km:
            return True, candidate
    return False, closest_point


def analyze_supply_routes(
    *,
    registry_path: Path,
    corridors_path: Path,
    risk_center: Tuple[float, float],
    radius_km: float,
    max_routes: int = 3,
    max_miles: float = 30.0,
    osrm_cache_path: Path | None = None,
) -> list[RouteImpact]:
    corridors = load_highway_corridors(corridors_path)
    impacts: list[RouteImpact] = []
    entries: Iterable[SMERegistryEntry] = load_registry(registry_path)
    for entry in entries:
        print(f"🚚 Building routes for {entry.name} ({entry.sme_id})")
        routes = generate_realistic_routes(
            sme_coords=(entry.latitude, entry.longitude),
            corridors=corridors,
            max_routes=max_routes,
            max_miles=max_miles,
            cache_path=osrm_cache_path,
        )
        print(f"   ↳ Generated {len(routes)} routes")
        for corridor_name, waypoints in routes:
            route = DeliveryRoute(
                origin=entry.name,
                destination=corridor_name,
                waypoints=[
                    {"lat": lat, "lon": lon} for lat, lon in waypoints
                ],
            )
            interrupted, intersection_point = is_route_interrupted(
                route=route,
                risk_center=risk_center,
                radius_km=radius_km,
            )
            impacts.append(
                RouteImpact(
                    sme_id=entry.sme_id,
                    name=entry.name,
                    origin=route.origin,
                    destination=route.destination,
                    interrupted=interrupted,
                    intersection_point=intersection_point if interrupted else None,
                    waypoints=waypoints,
                )
            )
    return impacts


def generate_risk_map(
    *,
    center: Tuple[float, float],
    radius_km: float,
    affected: Iterable[AffectedSME],
    safe: Iterable[AffectedSME],
    output_path: Path,
    route_impacts: Iterable[RouteImpact] | None = None,
    risk_center: Tuple[float, float] | None = None,
    risk_radius_km: float | None = None,
    label_colors: Tuple[str, str] = ("#8B0000", "#006400"),
    segment_colors: Tuple[str, str] = ("#FF6666", "#90EE90"),
    label_offset: Tuple[float, float] = (0.002, 0.002),
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

    affected_color, safe_color = label_colors
    risky_segment_color, safe_segment_color = segment_colors

    label_lat_offset, label_lon_offset = label_offset

    for sme in affected:
        if sme.latitude is None or sme.longitude is None:
            continue
        folium.Marker(
            location=(sme.latitude + label_lat_offset, sme.longitude + label_lon_offset),
            tooltip=sme.name,
            popup=f"{sme.name} — {sme.sector} ({sme.distance_km} km)",
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-size: 14pt; color: {affected_color}; '
                    'font-weight: bold;">'
                    f"{sme.name}"
                    "</div>"
                )
            ),
        ).add_to(map_view)

    for sme in safe:
        if sme.latitude is None or sme.longitude is None:
            continue
        folium.Marker(
            location=(sme.latitude + label_lat_offset, sme.longitude + label_lon_offset),
            tooltip=sme.name,
            popup=f"{sme.name} — {sme.sector} ({sme.distance_km} km)",
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-size: 14pt; color: {safe_color}; '
                    'font-weight: bold;">'
                    f"{sme.name}"
                    "</div>"
                )
            ),
        ).add_to(map_view)

    if route_impacts:
        for impact in route_impacts:
            for idx in range(len(impact.waypoints) - 1):
                start = impact.waypoints[idx]
                end = impact.waypoints[idx + 1]
                segment_intersects = False
                if risk_center and risk_radius_km is not None:
                    candidate = _closest_point_on_segment(start, end, risk_center)
                    distance_km = _distance_km(risk_center, candidate)
                    if distance_km <= risk_radius_km:
                        segment_intersects = True
                color = risky_segment_color if segment_intersects else safe_segment_color
                folium.PolyLine(
                    locations=[start, end],
                    color=color,
                    weight=3,
                    opacity=0.85,
                    tooltip=(
                        f"Path: {impact.origin} ➔ {impact.destination} | "
                        f"Status: {'CRITICAL BLOCKAGE' if segment_intersects else 'CLEAR'}"
                    ),
                ).add_to(map_view)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    map_view.save(str(output_path))


__all__ = [
    "RouteImpact",
    "analyze_supply_routes",
    "get_smes_in_radius",
    "generate_risk_map",
    "generate_realistic_routes",
    "is_route_interrupted",
    "load_highway_corridors",
]
