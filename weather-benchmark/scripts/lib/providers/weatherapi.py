"""
Prévisions WeatherAPI.com (clé gratuite nécessaire).
https://www.weatherapi.com/docs/
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from lib.http_util import httpx_get

PARIS = ZoneInfo("Europe/Paris")
BASE = "https://api.weatherapi.com/v1/forecast.json"


def _wind_dir_degree_from_hours(hours: list[dict[str, Any]]) -> float | None:
    """Prend la direction au pic de vent dans la journée (deg météo)."""
    best_kph = -1.0
    deg: float | None = None
    for h in hours:
        wk = h.get("wind_kph")
        if wk is None:
            continue
        try:
            wkf = float(wk)
        except (TypeError, ValueError):
            continue
        if wkf >= best_kph:
            best_kph = wkf
            wd = h.get("wind_degree")
            if wd is not None:
                try:
                    deg = float(wd)
                except (TypeError, ValueError):
                    deg = None
    return deg


def fetch_forecast(latitude: float, longitude: float, *, days: int = 10) -> dict[str, Any]:
    key = (os.getenv("WEATHERAPI_KEY") or os.getenv("WEATHERAPI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "WEATHERAPI_KEY manquant (.env ou variable d'environnement). "
            "Crée une clé sur https://www.weatherapi.com/"
        )
    params = {
        "key": key,
        "q": f"{latitude},{longitude}",
        "days": min(days, 14),
    }
    r = httpx_get(BASE, params=params, timeout=httpx.Timeout(60.0, connect=30.0))
    return r.json()


def daily_rows_for_city(
    issued_at: datetime,
    city_id: int,
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    data = fetch_forecast(lat, lon, days=10)
    today = datetime.now(PARIS).date()
    rows: list[dict[str, Any]] = []
    for i, fd in enumerate(data.get("forecast", {}).get("forecastday") or []):
        day_str = fd.get("date")
        if not day_str:
            continue
        try:
            d = date.fromisoformat(str(day_str))
        except ValueError:
            continue
        lead = (d - today).days
        if lead < 1 or lead > 7:
            continue
        day = fd.get("day") or {}
        hours = fd.get("hour") or []
        tmax = day.get("maxtemp_c")
        tmin = day.get("mintemp_c")
        tmean = day.get("avgtemp_c")
        if tmean is None and tmax is not None and tmin is not None:
            tmean = (float(tmax) + float(tmin)) / 2.0
        pp = day.get("daily_chance_of_rain")
        if pp is not None:
            pp = float(pp)
        wspd_kph = day.get("maxwind_kph")
        w_ms = float(wspd_kph) / 3.6 if wspd_kph is not None else None
        cond = day.get("condition") or {}
        code = cond.get("code")
        wd = _wind_dir_degree_from_hours(hours if isinstance(hours, list) else [])
        precip = day.get("totalprecip_mm")
        rows.append(
            {
                "city_id": city_id,
                "issued_at": issued_at,
                "valid_time": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                "lead_days": lead,
                "time_step": "daily",
                "temp_max_c": tmax,
                "temp_min_c": tmin,
                "temp_mean_c": tmean,
                "wind_speed_ms": w_ms,
                "wind_gust_ms": None,
                "wind_dir_deg": wd,
                "precip_prob": pp,
                "precip_amount_mm": precip,
                "cloud_cover_pct": None,
                "weather_code": int(code) if code is not None else None,
                "raw": {"source": "weatherapi", "forecastday_index": i},
            }
        )
    return rows
