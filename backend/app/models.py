from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

DEMO_METHOD = "demo_heuristic_v1"
DRY_RUN = "dry_run"


def now():
    return datetime.now(timezone.utc)


class Risk(Base):
    __tablename__ = "risk_assessments"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    location: Mapped[str] = mapped_column(String(160), index=True)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    river_level_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20))
    explanation: Mapped[str] = mapped_column(Text)
    # Which method produced the score, and whether that method has been scientifically validated.
    method: Mapped[str] = mapped_column(String(40), default=DEMO_METHOD, server_default=DEMO_METHOD)
    validated: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(160))
    threshold: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AlertEvent(Base):
    """Immutable log of 'this alert rule matched this assessment'.

    alert_id / assessment_id are soft references on purpose: the row keeps a snapshot of the
    rule so the history survives later edits or deletion of the rule.
    """

    __tablename__ = "alert_events"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    alert_id: Mapped[int] = mapped_column(index=True)
    alert_name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(160))
    threshold: Mapped[float] = mapped_column(Float)
    assessment_id: Mapped[int] = mapped_column(index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20))
    method: Mapped[str] = mapped_column(String(40))
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_status: Mapped[str] = mapped_column(String(20), default=DRY_RUN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SatelliteAnalysis(Base):
    """Metadata of a completed segmentation run. The image and mask themselves are NOT stored in the database."""

    __tablename__ = "satellite_analyses"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    bytes_received: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    model_name: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(80))
    weights_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    flooded_pixels: Mapped[int] = mapped_column(Integer)
    total_pixels: Mapped[int] = mapped_column(Integer)
    flooded_fraction: Mapped[float] = mapped_column(Float)
    flooded_area_km2: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
