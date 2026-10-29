"""Alert-rule evaluation (DRY RUN: records matches, never sends anything).

Trigger condition, exactly:
    rule.enabled
    AND normalize(rule.location) == normalize(assessment.location)
    AND assessment.risk_score >= rule.threshold
"""
from sqlalchemy.orm import Session

from ..models import DRY_RUN, Alert, AlertEvent, Risk


def normalize_location(value: str) -> str:
    return " ".join(value.split()).casefold()


def rule_matches(rule: Alert, location: str, score: float) -> bool:
    return (
        bool(rule.enabled)
        and normalize_location(rule.location) == normalize_location(location)
        and score >= rule.threshold
    )


def evaluate(db: Session, risk: Risk) -> list[AlertEvent]:
    """Add one AlertEvent per matching rule to the session (caller commits, so it is atomic with the assessment)."""
    events = []
    for rule in db.query(Alert).filter(Alert.enabled.is_(True)).order_by(Alert.id).all():
        if rule_matches(rule, risk.location, risk.risk_score):
            ev = AlertEvent(
                alert_id=rule.id,
                alert_name=rule.name,
                location=rule.location,
                threshold=rule.threshold,
                assessment_id=risk.id,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                method=risk.method,
                validated=risk.validated,
                delivery_status=DRY_RUN,
            )
            db.add(ev)
            events.append(ev)
    return events
