from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _as_utc(v: datetime) -> datetime:
    """SQLite/MySQL return naive datetimes; they are stored as UTC, so say so explicitly in the API."""
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)


UtcDateTime = Annotated[datetime, AfterValidator(_as_utc)]
Location = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class RiskIn(BaseModel):
    location: Location
    rainfall_mm: float = Field(ge=0, le=2000)
    river_level_m: float | None = Field(default=None, ge=0, le=1000)


class RiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    location: str
    rainfall_mm: float
    river_level_m: float | None
    risk_score: float
    risk_level: str
    explanation: str
    method: str
    validated: bool
    created_at: UtcDateTime


class AlertIn(BaseModel):
    name: Name
    location: Location
    threshold: float = Field(ge=0, le=100)
    enabled: bool = True


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location: str
    threshold: float
    enabled: bool
    created_at: UtcDateTime


class AlertEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_id: int
    alert_name: str
    location: str
    threshold: float
    assessment_id: int
    risk_score: float
    risk_level: str
    method: str
    validated: bool
    delivery_status: str
    created_at: UtcDateTime


class RiskCreateOut(RiskOut):
    """Response to creating an assessment: the saved row plus the alert rules it matched (dry-run only)."""

    triggered_alerts: list[AlertEventOut] = []


class SatelliteAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    bytes_received: int
    width: int
    height: int
    model_name: str
    model_version: str
    weights_sha256: str | None
    flooded_pixels: int
    total_pixels: int
    flooded_fraction: float
    flooded_area_km2: float | None
    inference_ms: float
    created_at: UtcDateTime
