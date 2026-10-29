from fastapi import APIRouter, Query

from ..services import weather as svc

router = APIRouter(prefix="/api", tags=["weather"])
DEFAULT_CITY = "Chennai"

CITY = Query(None, max_length=100, description="City name, e.g. 'Chennai' or 'Paris,FR'. Ignored when lat and lon are given.")
LAT = Query(None, ge=-90, le=90, description="Latitude (use with lon to skip geocoding)")
LON = Query(None, ge=-180, le=180, description="Longitude (use with lat to skip geocoding)")


@router.get("/weather", summary="CURRENT weather observation (not a forecast)")
def get_current_weather(city: str | None = CITY, lat: float | None = LAT, lon: float | None = LON):
    if city is None and lat is None and lon is None:
        city = DEFAULT_CITY
    return svc.current_observation(city, lat, lon)


@router.get("/weather/forecast", summary="Provider FORECAST in 3-hour steps (not observed, not a flood forecast)")
def get_weather_forecast(
    city: str | None = CITY,
    lat: float | None = LAT,
    lon: float | None = LON,
    periods: int = Query(8, ge=1, le=40, description="Number of 3-hour periods (max 40 = 5 days)"),
):
    if city is None and lat is None and lon is None:
        city = DEFAULT_CITY
    return svc.forecast(city, lat, lon, periods)
