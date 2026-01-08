from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, confloat, constr


class RiskSignal(BaseModel):
    """Type-safe representation of an external supply-chain risk signal.

    This is the core input to the AI control tower. It is intentionally minimal
    in v0.0.1 but is designed to be extended with richer metadata (e.g., sector,
    data source, timestamps) and linked to future RAG-based regulatory context.
    """

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

    class Config:
        frozen = True
        orm_mode = True
        extra = "forbid"


AlertPriority = Literal["LOW", "MEDIUM", "HIGH"]

