import logging

import pytest
import requests

from app.services.weather import CURRENT_URL, FORECAST_URL, GEO_URL

KEY = "secret-key-123"
GEO = [{"name": "Chennai", "country": "IN", "lat": 13.0827, "lon": 80.2707}]
CURRENT = {
    "name": "Chennai", "dt": 1790000000, "sys": {"country": "IN"},
    "main": {"temp": 30.5, "humidity": 70}, "rain": {"1h": 2.1},
    "weather": [{"description": "light rain"}],
}
FORECAST = {
    "city": {"country": "IN"},
    "list": [
        {"dt": 1790000000, "main": {"temp": 29.0, "humidity": 80}, "pop": 0.6, "rain": {"3h": 1.5}, "weather": [{"description": "light rain"}]},
        {"dt": 1790010800, "main": {"temp": 28.0, "humidity": 82}, "pop": 0.2, "weather": [{"description": "clouds"}]},
        {"dt": 1790021600, "main": {"temp": 27.5, "humidity": 85}, "pop": 0.9, "rain": {"3h": 4.0}, "weather": [{"description": "rain"}]},
    ],
}


class FakeResp:
    def __init__(self, status=200, payload=None, headers=None, bad_json=False):
        self.status_code, self.payload, self.headers, self.bad_json = status, payload, headers or {}, bad_json

    def json(self):
        if self.bad_json:
            raise ValueError("not json")
        return self.payload


class Provider:
    def __init__(self):
        self.routes, self.calls = {}, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {}), timeout))
        r = self.routes[url]  # KeyError => the code called an unexpected URL
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture()
def provider(monkeypatch):
    p = Provider()
    monkeypatch.setenv("OPENWEATHER_API_KEY", KEY)
    monkeypatch.setattr("app.services.weather.requests.get", p.get)
    return p


def urls(p):
    return [c[0] for c in p.calls]


# ---- not configured ----
def test_current_without_key_is_status_not_error(client, monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "")
    r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 200
    d = r.json()
    assert d["available"] is False and d["kind"] == "current_observation" and "OPENWEATHER_API_KEY" in d["message"]


def test_forecast_without_key(client, monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "")
    d = client.get("/api/weather/forecast").json()
    assert d["available"] is False and d["kind"] == "forecast" and d["periods"] == []


# ---- current observation ----
def test_current_success_geocodes_then_fetches_by_coordinates(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), CURRENT_URL: FakeResp(payload=CURRENT)}
    d = client.get("/api/weather?city=Chennai").json()
    assert urls(provider) == [GEO_URL, CURRENT_URL]
    assert provider.calls[1][1]["lat"] == 13.0827 and provider.calls[1][1]["lon"] == 80.2707
    assert provider.calls[1][1]["units"] == "metric"
    assert all(c[2] == 8 for c in provider.calls)  # timeout on every call
    assert d["kind"] == "current_observation" and d["available"] is True
    assert d["temperature_c"] == 30.5 and d["rainfall_mm_1h"] == 2.1 and d["country"] == "IN"
    assert d["observed_at"].endswith("+00:00")


def test_missing_rain_is_none_not_zero(client, provider):
    payload = {k: v for k, v in CURRENT.items() if k != "rain"}
    provider.routes = {GEO_URL: FakeResp(payload=GEO), CURRENT_URL: FakeResp(payload=payload)}
    d = client.get("/api/weather?city=Chennai").json()
    assert d["rainfall_mm_1h"] is None


def test_default_city_is_used_when_no_location_given(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), CURRENT_URL: FakeResp(payload=CURRENT)}
    client.get("/api/weather")
    assert provider.calls[0][1]["q"] == "Chennai"


def test_lat_lon_skips_geocoding(client, provider):
    provider.routes = {CURRENT_URL: FakeResp(payload=CURRENT)}
    d = client.get("/api/weather?lat=13.08&lon=80.27").json()
    assert urls(provider) == [CURRENT_URL]
    assert d["lat"] == 13.08 and d["city"] == "Chennai"


def test_geocode_result_is_cached(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), CURRENT_URL: FakeResp(payload=CURRENT)}
    client.get("/api/weather?city=Chennai")
    client.get("/api/weather?city=Chennai")
    assert urls(provider).count(GEO_URL) == 1


# ---- location errors ----
def test_unknown_city_is_404(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=[])}
    r = client.get("/api/weather?city=Nowhereville")
    assert r.status_code == 404 and r.json()["code"] == "location_not_found"
    assert "Nowhereville" in r.json()["detail"]


def test_empty_city_is_422(client, provider):
    r = client.get("/api/weather?city=%20%20")
    assert r.status_code == 422 and r.json()["code"] == "invalid_location"
    assert provider.calls == []


def test_only_one_coordinate_is_422(client, provider):
    r = client.get("/api/weather?lat=13.0")
    assert r.status_code == 422 and r.json()["code"] == "invalid_location"


def test_out_of_range_coordinates_rejected(client, provider):
    assert client.get("/api/weather?lat=95&lon=10").status_code == 422
    assert client.get("/api/weather?lat=10&lon=181").status_code == 422
    assert provider.calls == []


# ---- provider failures ----
def test_invalid_key_maps_to_502_without_leaking_key(client, provider):
    provider.routes = {GEO_URL: FakeResp(status=401, payload={"cod": 401})}
    r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 502 and r.json()["code"] == "weather_auth_failed"
    assert KEY not in r.text


def test_rate_limit_maps_to_429_with_retry_after(client, provider):
    provider.routes = {GEO_URL: FakeResp(status=429, headers={"Retry-After": "30"})}
    r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 429 and r.json()["code"] == "weather_rate_limited"
    assert r.headers["retry-after"] == "30"


def test_non_numeric_retry_after_is_dropped(client, provider):
    provider.routes = {GEO_URL: FakeResp(status=429, headers={"Retry-After": "soon\r\nX: y"})}
    r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 429 and "retry-after" not in r.headers


def test_timeout_maps_to_504(client, provider):
    provider.routes = {GEO_URL: requests.Timeout("slow")}
    r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 504 and r.json()["code"] == "weather_timeout"


def test_network_error_maps_to_502_and_is_not_logged_with_key(client, provider, caplog):
    provider.routes = {GEO_URL: requests.ConnectionError(f"https://x/?appid={KEY}")}
    with caplog.at_level(logging.DEBUG):
        r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 502 and r.json()["code"] == "weather_unreachable"
    assert KEY not in r.text and KEY not in caplog.text


def test_provider_500_maps_to_502(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), CURRENT_URL: FakeResp(status=500)}
    r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 502 and r.json()["code"] == "weather_provider_error"


def test_unreadable_json_maps_to_502(client, provider):
    provider.routes = {GEO_URL: FakeResp(bad_json=True)}
    r = client.get("/api/weather?city=Chennai")
    assert r.status_code == 502 and r.json()["code"] == "weather_bad_response"


def test_malformed_current_payload_maps_to_502(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), CURRENT_URL: FakeResp(payload=["unexpected"])}
    assert client.get("/api/weather?city=Chennai").json()["code"] == "weather_bad_response"


# ---- forecast ----
def test_forecast_success_is_labelled_and_summarised(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), FORECAST_URL: FakeResp(payload=FORECAST)}
    d = client.get("/api/weather/forecast?city=Chennai&periods=3").json()
    assert provider.calls[1][1]["cnt"] == 3
    assert d["kind"] == "forecast" and d["step_hours"] == 3 and len(d["periods"]) == 3
    assert "not a validated flood forecast" in d["message"]
    assert d["periods"][0]["precipitation_probability"] == 0.6 and d["periods"][0]["rainfall_mm_3h"] == 1.5
    assert d["periods"][1]["rainfall_mm_3h"] is None  # not reported, not assumed 0
    assert d["reported_rain_periods"] == 2 and d["total_rainfall_mm_reported"] == 5.5


def test_forecast_with_no_reported_rain_has_null_total(client, provider):
    payload = {"list": [{"dt": 1790000000, "main": {"temp": 30}, "pop": 0.0, "weather": []}]}
    provider.routes = {GEO_URL: FakeResp(payload=GEO), FORECAST_URL: FakeResp(payload=payload)}
    d = client.get("/api/weather/forecast?city=Chennai").json()
    assert d["total_rainfall_mm_reported"] is None and d["reported_rain_periods"] == 0


def test_forecast_periods_validated(client, provider):
    assert client.get("/api/weather/forecast?periods=0").status_code == 422
    assert client.get("/api/weather/forecast?periods=41").status_code == 422
    assert provider.calls == []


def test_forecast_malformed_payload(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), FORECAST_URL: FakeResp(payload={"list": "nope"})}
    assert client.get("/api/weather/forecast?city=Chennai").json()["code"] == "weather_bad_response"


def test_forecast_provider_404(client, provider):
    provider.routes = {GEO_URL: FakeResp(payload=GEO), FORECAST_URL: FakeResp(status=404)}
    assert client.get("/api/weather/forecast?city=Chennai").status_code == 404
