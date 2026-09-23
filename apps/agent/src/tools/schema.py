from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, confloat, constr


class PolicySnippet(BaseModel):
    """A single retrieved snippet from a legislative or policy document."""

    text: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Raw text content of the retrieved snippet."
    )
    page: int = Field(
        ...,
        ge=1,
        description="1-based page number within the source document.",
    )
    score: confloat(ge=0.0) = Field(
        ...,
        description=(
            "Similarity score from the vector store. "
            "Lower or higher is backend-dependent but must be comparable within a query."
        ),
    )
    source_path: Path = Field(
        ...,
        description="Filesystem path to the source document (e.g., S.257 PDF).",
    )
    source_title: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Human-readable title or label for the source document.",
    )


class PolicyQueryResult(BaseModel):
    """Typed result of a policy-aware RAG query over legislative text."""

    query: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Original natural-language query string."
    )
    snippets: List[PolicySnippet] = Field(
        default_factory=list,
        description="Ordered list of the most relevant policy snippets for this query.",
    )


class GeoCenter(BaseModel):
    """Geospatial epicenter metadata for a risk signal."""

    lat: confloat(ge=-90.0, le=90.0) = Field(
        ..., description="Latitude of the epicenter.",
    )
    lon: confloat(ge=-180.0, le=180.0) = Field(
        ..., description="Longitude of the epicenter.",
    )
    impact_radius_km: confloat(gt=0.0) = Field(
        ..., description="Impact radius in kilometers.",
    )


class RiskSignal(BaseModel):
    """Type-safe representation of an external supply-chain risk signal."""

    risk_score: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Normalized risk score in [0.0, 1.0] representing severity.",
    )
    location: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Human-readable location descriptor (e.g., county, city, region).",
    )
    primary_driver: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Primary driver of the risk (e.g., port disruption, storm, cyber incident).",
    )
    estimated_impact: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Short narrative estimate of the potential supply-chain impact.",
    )
    geo_center: GeoCenter = Field(
        ..., description="Geospatial epicenter and radius for the risk signal.",
    )

    class Config:
        frozen = True
        from_attributes = True
        extra = "forbid"


AlertPriority = Literal["LOW", "MEDIUM", "HIGH"]


class AffectedSME(BaseModel):
    """Minimal representation of a potentially affected SME."""

    sme_id: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Stable identifier for the SME in the local registry.",
    )
    name: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Legal or common name of the SME.",
    )
    county: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="County or equivalent sub-national unit.",
    )
    sector: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Simple sector label (e.g., agriculture, logistics).",
    )
    latitude: confloat(ge=-90.0, le=90.0) | None = Field(
        default=None, description="Latitude of the SME location.",
    )
    longitude: confloat(ge=-180.0, le=180.0) | None = Field(
        default=None, description="Longitude of the SME location.",
    )
    distance_km: confloat(ge=0.0) | None = Field(
        default=None, description="Distance in kilometers from the risk epicenter.",
    )


class ResilienceReport(BaseModel):
    """Structured representation of a generated resilience / alert report."""

    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the report was generated.",
    )
    priority: AlertPriority = Field(
        ..., description="Derived alert priority for the risk signal.",
    )
    risk_signal: RiskSignal = Field(
        ..., description="The original validated risk signal driving this report.",
    )
    affected_smes: List[AffectedSME] = Field(
        default_factory=list,
        description="List of SMEs potentially affected within the target geography.",
    )
    markdown_alert: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Markdown-formatted supply chain alert.",
    )
    notes: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None,
        description="Optional internal notes or caveats (e.g., data quality, assumptions).",
    )


__all__ = [
    "AffectedSME",
    "AlertPriority",
    "GeoCenter",
    "PolicyQueryResult",
    "PolicySnippet",
    "ResilienceReport",
    "RiskSignal",
]

