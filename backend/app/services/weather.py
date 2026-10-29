"""OpenWeather client.

Two clearly separate products are exposed:
  * current_observation(): what the provider reports NOW (kind="current_observation")
  * forecast():            provider's atmospheric forecast (kind="forecast")
Neither is a validated flood forecast.

Provider endpoints used (all free-tier): Geocoding /geo/1.0/direct,
Current /data/2.5/weather, 5-day/3-hour forecast /data/2.5/forecast.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

import requests

from ..config import settings
from ..errors import ApiError

logger = logging.getLogger(__name__)

BASE = "https://api.openweathermap.org"
GEO_URL = f"{BASE}/geo/1.0/direct"
CURRENT_URL = f"{BASE}/data/2.5/weather"
FORECAST_URL = f"{BASE}/data/2.5/forecast"
TIMEOUT = 8  # seconds, applied to every provider call


class WeatherError(ApiError):
    """A typed, user-readable weather failure."""


@dataclass(frozen=True)
class Location:
    name: str
    country: str | None
    lat: float
    lon: float

    def as_dict(self) -> dict:
        return {"name": self.name, "country": self.country, "lat": self.lat, "lon": self.lon}


# ---------------------------------------------------------------- provider access
def _get_json(url: str, params: dict):
    """GET a provider URL and translate every failure into a WeatherError.

    Never logs params or exception text: both can contain the API key.
    """
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.Timeout:
        logger.warning("OpenWeather request timed out")
        raise WeatherError(504, "weather_timeout", "The weather provider timed out. Try again shortly.")
    except requests.RequestException as exc:
        logger.warning("OpenWeather request failed: %s", type(exc).__name__)
        raise WeatherError(502, "weather_unreachable", "Could not reach the weather provider. Check the network connection.")

    status = r.status_code
    if status == 401:
        raise WeatherError(502, "weather_auth_failed", "The weather provider rejected the configured API key (it may be invalid or not yet activated).")
    if status == 404:
        raise WeatherError(404, "location_not_found", "The weather provider has no data for that location.")
    if status == 429:
        retry = r.headers.get("Retry-After") if getattr(r, "headers", None) else None
        retry = retry if retry and retry.isdigit() else None
        raise WeatherError(429, "weather_rate_limited", "Weather provider rate limit reached. Wait a moment and retry.", retry)
    if status >= 400:
        logger.warning("OpenWeather returned HTTP %s", status)
        raise WeatherError(502, "weather_provider_error", f"The weather provider returned an error (HTTP {status}).")
    try:
        return r.json()
    except ValueError:
        raise WeatherError(502, "weather_bad_response", "The weather provider returned an unreadable response.")


def _unavailable(kind: str, city: str | None, message: str) -> dict:
    """Not-configured state. Returned as HTTP 200 so the dashboard can render it as a status, not a crash."""
    base = {
        "available": False,
        "kind": kind,
        "city": city,
        "message": message,
    }
    if kind == "current_observation":
        base.update(temperature_c=None, humidity_pct=None, rainfall_mm_1h=None, description=None, observed_at=None)
    else:
        base.update(periods=[], total_rainfall_mm_reported=None)
    return base


def _iso(ts) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


# ---------------------------------------------------------------- location
@lru_cache(maxsize=128)
def geocode(city: str) -> Location:
    data = _get_json(GEO_URL, {"q": city, "limit": 1, "appid": settings.openweather_api_key})
    if not data:
        raise WeatherError(404, "location_not_found", f"Location not found: {city}")
    try:
        g = data[0]
        return Location(g.get("name") or city, g.get("country"), float(g["lat"]), float(g["lon"]))
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        raise WeatherError(502, "weather_bad_response", "The geocoding response was not understood.")


def resolve_location(city: str | None, lat: float | None, lon: float | None) -> Location:
    if (lat is None) != (lon is None):
        raise WeatherError(422, "invalid_location", "Provide both lat and lon, or neither.")
    if lat is not None:
        name = (city or "").strip() or f"{lat:.4f}, {lon:.4f}"
        return Location(name, None, lat, lon)
    name = (city or "").strip()
    if not name:
        raise WeatherError(422, "invalid_location", "City name must not be empty.")
    return geocode(name)


# ---------------------------------------------------------------- products
def current_observation(city: str | None, lat: float | None = None, lon: float | None = None) -> dict:
    kind = "current_observation"
    key = settings.openweather_api_key
    if not key:
        return _unavailable(kind, city, "Set OPENWEATHER_API_KEY in backend/.env")
    loc = resolve_location(city, lat, lon)
    d = _get_json(CURRENT_URL, {"lat": loc.lat, "lon": loc.lon, "appid": key, "units": "metric"})
    if not isinstance(d, dict):
        raise WeatherError(502, "weather_bad_response", "The weather provider returned an unexpected response.")
    main = d.get("main") or {}
    rain = d.get("rain") or {}
    name = loc.name if loc.country else (d.get("name") or loc.name)
    return {
        "available": True,
        "kind": kind,
        "message": "Current OpenWeather observation (not a forecast)",
        "city": name,
        "country": loc.country or (d.get("sys") or {}).get("country"),
        "lat": loc.lat,
        "lon": loc.lon,
        "observed_at": _iso(d.get("dt")),
        "temperature_c": main.get("temp"),
        "humidity_pct": main.get("humidity"),
        # None means the provider reported no rain value; it is NOT assumed to be 0.
        "rainfall_mm_1h": rain.get("1h"),
        "rainfall_mm_3h": rain.get("3h"),
        "description": (d.get("weather") or [{}])[0].get("description"),
    }


def forecast(city: str | None, lat: float | None = None, lon: float | None = None, periods: int = 8) -> dict:
    kind = "forecast"
    key = settings.openweather_api_key
    if not key:
        return _unavailable(kind, city, "Set OPENWEATHER_API_KEY in backend/.env")
    loc = resolve_location(city, lat, lon)
    d = _get_json(FORECAST_URL, {"lat": loc.lat, "lon": loc.lon, "appid": key, "units": "metric", "cnt": periods})
    if not isinstance(d, dict) or not isinstance(d.get("list"), list):
        raise WeatherError(502, "weather_bad_response", "The weather provider returned an unexpected forecast response.")
    out = []
    for item in d["list"]:
        main = item.get("main") or {}
        rain = item.get("rain") or {}
        out.append({
            "time": _iso(item.get("dt")),
            "temperature_c": main.get("temp"),
            "humidity_pct": main.get("humidity"),
            "precipitation_probability": item.get("pop"),  # 0..1 as reported by the provider
            "rainfall_mm_3h": rain.get("3h"),  # None = not reported
            "description": (item.get("weather") or [{}])[0].get("description"),
        })
    reported = [p["rainfall_mm_3h"] for p in out if p["rainfall_mm_3h"] is not None]
    city_info = d.get("city") or {}
    return {
        "available": True,
        "kind": kind,
        "message": "OpenWeather 5-day/3-hour atmospheric forecast. Not observed data and not a validated flood forecast.",
        "city": loc.name,
        "country": loc.country or city_info.get("country"),
        "lat": loc.lat,
        "lon": loc.lon,
        "step_hours": 3,
        "periods": out,
        "reported_rain_periods": len(reported),
        "total_rainfall_mm_reported": round(sum(reported), 2) if reported else None,
    }
