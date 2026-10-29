def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_configured": False, "model_state": "not_configured"}


def test_openapi_lists_all_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/api/health", "/api/weather", "/api/risk-assessments", "/api/satellite/analyze", "/api/alerts"):
        assert p in paths


# ---- risk ----
def test_risk_create_and_list(client):
    r = client.post("/api/risk-assessments", json={"location": " Chennai ", "rainfall_mm": 55})
    assert r.status_code == 200
    body = r.json()
    assert body["risk_score"] == 25.7 and body["risk_level"] == "Low" and body["location"] == "Chennai"
    assert "not a validated" in body["explanation"]
    assert len(client.get("/api/risk-assessments").json()) == 1


def test_risk_levels(client):
    hi = client.post("/api/risk-assessments", json={"location": "X", "rainfall_mm": 150, "river_level_m": 8}).json()
    assert hi["risk_score"] == 100 and hi["risk_level"] == "High"
    mid = client.post("/api/risk-assessments", json={"location": "X", "rainfall_mm": 80}).json()
    assert mid["risk_level"] == "Moderate"


def test_risk_validation_errors(client):
    assert client.post("/api/risk-assessments", json={"location": "", "rainfall_mm": 1}).status_code == 422
    assert client.post("/api/risk-assessments", json={"location": "X", "rainfall_mm": -1}).status_code == 422
    assert client.post("/api/risk-assessments", json={"location": "X", "rainfall_mm": 5000}).status_code == 422


def test_risk_list_limit_is_clamped(client):
    for _ in range(3):
        client.post("/api/risk-assessments", json={"location": "X", "rainfall_mm": 1})
    assert len(client.get("/api/risk-assessments?limit=0").json()) == 1
    assert len(client.get("/api/risk-assessments?limit=2").json()) == 2


# ---- alerts ----
def test_alert_create_list_delete(client):
    a = client.post("/api/alerts", json={"name": "Rain", "location": "Chennai", "threshold": 70}).json()
    assert a["enabled"] is True
    assert [x["id"] for x in client.get("/api/alerts").json()] == [a["id"]]
    assert client.delete(f"/api/alerts/{a['id']}").json() == {"deleted": True}
    assert client.get("/api/alerts").json() == []


def test_alert_delete_missing_and_validation(client):
    assert client.delete("/api/alerts/999").status_code == 404
    assert client.post("/api/alerts", json={"name": "R", "location": "C", "threshold": 101}).status_code == 422


# ---- satellite upload (placeholder behaviour) ----


def test_upload_rejects_bad_extension(client):
    assert client.post("/api/satellite/analyze", files={"file": ("a.exe", b"1", "application/octet-stream")}).status_code == 400


def test_upload_rejects_oversize(client, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_MB", "0.001")  # ~1 KB
    r = client.post("/api/satellite/analyze", files={"file": ("a.png", b"x" * 5000, "image/png")})
    assert r.status_code == 413
