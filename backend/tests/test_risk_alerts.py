import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text, create_engine

from app.main import app


def mk_alert(client, name="Rain watch", location="Chennai", threshold=20, enabled=True):
    r = client.post("/api/alerts", json={"name": name, "location": location, "threshold": threshold, "enabled": enabled})
    assert r.status_code == 200
    return r.json()


def assess(client, location="Chennai", rain=55, river=None):
    body = {"location": location, "rainfall_mm": rain}
    if river is not None:
        body["river_level_m"] = river
    r = client.post("/api/risk-assessments", json=body)
    assert r.status_code == 200
    return r.json()


# ---- method labelling and time zones ----
def test_assessment_is_labelled_demo_and_unvalidated(client):
    d = assess(client)
    assert d["method"] == "demo_heuristic_v1" and d["validated"] is False
    listed = client.get("/api/risk-assessments").json()[0]
    assert listed["method"] == "demo_heuristic_v1" and listed["validated"] is False


def test_datetimes_are_explicit_utc(client):
    d = assess(client)
    assert d["created_at"].endswith("+00:00") or d["created_at"].endswith("Z")
    a = mk_alert(client)
    assert a["created_at"].endswith("+00:00") or a["created_at"].endswith("Z")


def test_blank_location_rejected(client):
    assert client.post("/api/risk-assessments", json={"location": "   ", "rainfall_mm": 1}).status_code == 422
    assert client.post("/api/alerts", json={"name": "  ", "location": "X", "threshold": 1}).status_code == 422


# ---- alert update / get ----
def test_alert_get_and_update(client):
    a = mk_alert(client)
    assert client.get(f"/api/alerts/{a['id']}").json()["name"] == "Rain watch"
    r = client.put(f"/api/alerts/{a['id']}", json={"name": "  Renamed ", "location": "Madurai", "threshold": 55, "enabled": False})
    assert r.status_code == 200
    d = r.json()
    assert (d["name"], d["location"], d["threshold"], d["enabled"]) == ("Renamed", "Madurai", 55, False)
    assert d["id"] == a["id"] and d["created_at"] == a["created_at"]


def test_alert_update_errors(client):
    assert client.put("/api/alerts/999", json={"name": "a", "location": "b", "threshold": 1}).status_code == 404
    assert client.get("/api/alerts/999").status_code == 404
    a = mk_alert(client)
    assert client.put(f"/api/alerts/{a['id']}", json={"name": "a", "location": "b", "threshold": 150}).status_code == 422
    assert client.get(f"/api/alerts/{a['id']}").json()["threshold"] == 20  # unchanged after failed update


# ---- evaluation (dry run) ----
def test_matching_rule_creates_dry_run_event(client):
    a = mk_alert(client, threshold=20)
    d = assess(client, rain=55)  # score 25.7
    assert len(d["triggered_alerts"]) == 1
    ev = d["triggered_alerts"][0]
    assert ev["alert_id"] == a["id"] and ev["assessment_id"] == d["id"]
    assert ev["delivery_status"] == "dry_run" and ev["validated"] is False
    assert ev["risk_score"] == 25.7 and ev["threshold"] == 20
    assert client.get("/api/alert-events").json()[0]["id"] == ev["id"]


def test_below_threshold_does_not_trigger(client):
    mk_alert(client, threshold=30)
    assert assess(client, rain=55)["triggered_alerts"] == []
    assert client.get("/api/alert-events").json() == []


def test_threshold_boundary_is_inclusive(client):
    mk_alert(client, threshold=70)
    d = assess(client, rain=150)  # exactly 70.0
    assert d["risk_score"] == 70.0 and len(d["triggered_alerts"]) == 1


def test_disabled_rule_does_not_trigger(client):
    mk_alert(client, enabled=False)
    assert assess(client)["triggered_alerts"] == []


def test_other_location_does_not_trigger(client):
    mk_alert(client, location="Madurai")
    assert assess(client, location="Chennai")["triggered_alerts"] == []


def test_location_match_ignores_case_and_extra_spaces(client):
    mk_alert(client, location="New  Delhi")
    assert len(assess(client, location=" new delhi ")["triggered_alerts"]) == 1


def test_location_match_is_exact_not_substring(client):
    mk_alert(client, location="Chennai")
    assert assess(client, location="Chennai, IN")["triggered_alerts"] == []


def test_multiple_matching_rules_each_get_an_event(client):
    mk_alert(client, name="A", threshold=10)
    mk_alert(client, name="B", threshold=25)
    mk_alert(client, name="C", threshold=90)
    names = sorted(e["alert_name"] for e in assess(client, rain=55)["triggered_alerts"])
    assert names == ["A", "B"]


def test_events_survive_rule_edit_and_delete(client):
    a = mk_alert(client, threshold=20)
    assess(client)
    client.put(f"/api/alerts/{a['id']}", json={"name": "Changed", "location": "Elsewhere", "threshold": 99})
    client.delete(f"/api/alerts/{a['id']}")
    ev = client.get("/api/alert-events").json()
    assert len(ev) == 1 and ev[0]["alert_name"] == "Rain watch" and ev[0]["location"] == "Chennai"


def test_event_limit_is_clamped(client):
    mk_alert(client, threshold=0)
    for _ in range(3):
        assess(client)
    assert len(client.get("/api/alert-events?limit=0").json()) == 1
    assert len(client.get("/api/alert-events?limit=2").json()) == 2


def test_failed_validation_creates_nothing(client):
    mk_alert(client, threshold=0)
    assert client.post("/api/risk-assessments", json={"location": "Chennai", "rainfall_mm": -5}).status_code == 422
    assert client.get("/api/risk-assessments").json() == [] and client.get("/api/alert-events").json() == []


def test_assessment_and_events_are_atomic(client, monkeypatch):
    mk_alert(client, threshold=0)

    def boom(db, risk):
        raise RuntimeError("evaluation failed")

    monkeypatch.setattr("app.routers.risk.evaluate", boom)
    with TestClient(app, raise_server_exceptions=False) as c:
        assert c.post("/api/risk-assessments", json={"location": "Chennai", "rainfall_mm": 55}).status_code == 500
    assert client.get("/api/risk-assessments").json() == []  # assessment rolled back too
    assert client.get("/api/alert-events").json() == []


# ---- schema upgrade of a database created by Phase 1/2 ----
def test_additive_migration_upgrades_old_risk_table(tmp_path):
    from app import models  # noqa: F401  (registers tables on Base)
    from app.database import ensure_schema

    eng = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with eng.begin() as c:
        c.execute(text(
            "CREATE TABLE risk_assessments (id INTEGER PRIMARY KEY, location VARCHAR(160), rainfall_mm FLOAT, "
            "river_level_m FLOAT, risk_score FLOAT, risk_level VARCHAR(20), explanation TEXT, created_at DATETIME)"))
        c.execute(text(
            "INSERT INTO risk_assessments (location, rainfall_mm, risk_score, risk_level, explanation, created_at) "
            "VALUES ('Old', 10, 4.7, 'Low', 'x', '2026-01-01 00:00:00')"))
    ensure_schema(eng)
    ensure_schema(eng)  # idempotent
    assert {"method", "validated"} <= {c["name"] for c in inspect(eng).get_columns("risk_assessments")}
    with eng.connect() as c:
        row = c.execute(text("SELECT method, validated FROM risk_assessments")).one()
    assert tuple(row) == ("demo_heuristic_v1", 0)
    assert inspect(eng).has_table("alert_events")
    eng.dispose()
