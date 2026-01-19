from __future__ import annotations

from pathlib import Path
from typing import List

import json
from pydantic import BaseModel, Field, ValidationError, confloat, constr

from src.models.report import AffectedSME


class SMERegistryEntry(BaseModel):
    """Internal representation of an SME in the local registry."""

    sme_id: constr(strip_whitespace=True, min_length=1) = Field(...)
    name: constr(strip_whitespace=True, min_length=1) = Field(...)
    county: constr(strip_whitespace=True, min_length=1) = Field(...)
    sector: constr(strip_whitespace=True, min_length=1) = Field(...)
    latitude: float = Field(..., description="Latitude of the SME location.")
    longitude: float = Field(..., description="Longitude of the SME location.")
    delivery_routes: list["DeliveryRoute"] = Field(default_factory=list)


class RouteWaypoint(BaseModel):
    lat: confloat(ge=-90.0, le=90.0) = Field(...)
    lon: confloat(ge=-180.0, le=180.0) = Field(...)


class DeliveryRoute(BaseModel):
    origin: constr(strip_whitespace=True, min_length=1) = Field(...)
    destination: constr(strip_whitespace=True, min_length=1) = Field(...)
    waypoints: list[RouteWaypoint] = Field(min_length=2)


def _load_registry(registry_path: Path) -> List[SMERegistryEntry]:
    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):  # pragma: no cover - simple guard
        raise ValueError("sme_registry.json must contain a list of SME entries")
    entries: List[SMERegistryEntry] = []
    for item in raw:
        try:
            entries.append(SMERegistryEntry.model_validate(item))
        except ValidationError as exc:  # pragma: no cover - logging hook
            # In a fuller implementation, we would log this and continue.
            raise exc
    return entries


def load_registry(registry_path: Path) -> List[SMERegistryEntry]:
    """Public wrapper for loading registry entries."""

    return _load_registry(registry_path)


def find_smes_by_location(
    *, registry_path: Path, location: str
) -> List[AffectedSME]:
    """Find SMEs whose county string is contained in the provided location.

    This is a deliberately simple v0.0.1 heuristic suitable for a Monterey County
    sandbox. Future versions can use geocoding, ZIP code, census tracts, etc.
    """

    normalized_location = location.lower()
    entries = _load_registry(registry_path)
    affected: List[AffectedSME] = []
    for entry in entries:
        county_lower = entry.county.lower()
        # Match either:
        # - full county string contained in the location, or
        # - location token (e.g., "monterey") contained in the county name.
        if county_lower in normalized_location or normalized_location in county_lower:
            affected.append(
                AffectedSME(
                    sme_id=entry.sme_id,
                    name=entry.name,
                    county=entry.county,
                    sector=entry.sector,
                    latitude=entry.latitude,
                    longitude=entry.longitude,
                )
            )
    return affected


__all__ = [
    "SMERegistryEntry",
    "DeliveryRoute",
    "RouteWaypoint",
    "find_smes_by_location",
    "load_registry",
]

