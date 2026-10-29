from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Risk
from ..schemas import AlertEventOut, RiskCreateOut, RiskOut
from ..schemas import RiskIn
from ..services.alerts import evaluate
from ..services.risk import assess

router = APIRouter(prefix="/api", tags=["risk"])


@router.post(
    "/risk-assessments",
    response_model=RiskCreateOut,
    summary="Create a DEMO risk assessment and dry-run evaluate alert rules",
)
def add_risk(p: RiskIn, db: Session = Depends(get_db)):
    result = assess(p.rainfall_mm, p.river_level_m)
    row = Risk(
        location=p.location,
        rainfall_mm=p.rainfall_mm,
        river_level_m=p.river_level_m,
        risk_score=result.score,
        risk_level=result.level,
        explanation=result.explanation,
        method=result.method,
        validated=result.validated,
    )
    db.add(row)
    db.flush()  # assigns row.id; nothing is committed yet
    events = evaluate(db, row)
    db.commit()  # assessment and alert events succeed or fail together
    db.refresh(row)
    return RiskCreateOut(
        **RiskOut.model_validate(row).model_dump(),
        triggered_alerts=[AlertEventOut.model_validate(e) for e in events],
    )


@router.get("/risk-assessments", response_model=list[RiskOut], summary="List assessment history")
def list_risks(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Risk).order_by(Risk.id.desc()).limit(max(1, min(limit, 200))).all()
