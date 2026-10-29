from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alert, AlertEvent
from ..schemas import AlertEventOut, AlertIn, AlertOut

router = APIRouter(prefix="/api", tags=["alerts"])


def _get_or_404(db: Session, alert_id: int) -> Alert:
    row = db.get(Alert, alert_id)
    if not row:
        raise HTTPException(404, "Alert not found")
    return row


@router.get("/alerts", response_model=list[AlertOut], summary="List alert rules")
def list_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).order_by(Alert.id.desc()).all()


@router.get("/alerts/{alert_id}", response_model=AlertOut, summary="Get one alert rule")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, alert_id)


@router.post("/alerts", response_model=AlertOut, summary="Create an alert rule")
def add_alert(p: AlertIn, db: Session = Depends(get_db)):
    row = Alert(name=p.name, location=p.location, threshold=p.threshold, enabled=p.enabled)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/alerts/{alert_id}", response_model=AlertOut, summary="Replace an alert rule (also used to enable/disable)")
def update_alert(alert_id: int, p: AlertIn, db: Session = Depends(get_db)):
    row = _get_or_404(db, alert_id)
    row.name, row.location, row.threshold, row.enabled = p.name, p.location, p.threshold, p.enabled
    db.commit()
    db.refresh(row)
    return row


@router.delete("/alerts/{alert_id}", summary="Delete an alert rule (its past trigger events are kept)")
def remove_alert(alert_id: int, db: Session = Depends(get_db)):
    row = _get_or_404(db, alert_id)
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/alert-events", response_model=list[AlertEventOut], summary="Dry-run trigger log (nothing is delivered)")
def list_alert_events(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(AlertEvent).order_by(AlertEvent.id.desc()).limit(max(1, min(limit, 200))).all()
