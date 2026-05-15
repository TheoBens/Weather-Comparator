"""
Tomorrow.io Weather Forecast (cle API).
https://docs.tomorrow.io/reference/weather-forecast
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from lib.http_util import httpx_get

PARIS = ZoneInfo("Europe/Paris")
BASE = "https://api.tomorrow.io/v4/weather/forecast"


def fetch_forecast_daily(latitude: float, longitude: float) -> dict[str, Any]:
    key = (os.getenv("TOMORROW_IO_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "TOMORROW_IO_API_KEY manquant (.env). Voir https://www.tomorrow.io/weather-api/"
        )
    loc = f"{latitude},{longitude}"
    params = {
        "location": loc,
        "timesteps": "1d",
        "apikey": key,
        "units": "metric",
    }
    try:
        r = httpx_get(BASE, params=params, timeout=httpx.Timeout(90.0, connect=45.0))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise RuntimeError(
                "Tomorrow.io refuse la cle (401). Verifie TOMORROW_IO_API_KEY dans scripts/.env "
                "(copie depuis le tableau Tomorrow.io), quotas du plan, ou regeneration de cle."
            ) from e
        raise
    return r.json()


def daily_rows_for_city(
    issued_at: datetime,
    city_id: int,
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    data = fetch_forecast_daily(lat, lon)
    today = datetime.now(PARIS).date()
    timelines = data.get("timelines") or {}
    daily: list[Any] = timelines.get("daily") or []
    if not daily:
        for _k, v in timelines.items():
            if not isinstance(v, list) or len(v) < 1:
                continue
            first = v[0]
            if not isinstance(first, dict):
                continue
            vals = first.get("values") or {}
            has_time = bool(first.get("time") or first.get("startTime"))
            has_vals = isinstance(vals, dict) and vals
            flat_temp = "temperatureMax" in first
            if has_time and (has_vals or flat_temp):
                daily = v
                break

    rows: list[dict[str, Any]] = []
    for i, block in enumerate(daily):
        time_s = block.get("time") or block.get("startTime")
        if not time_s:
            continue
        try:
            t_utc = datetime.fromisoformat(str(time_s).replace("Z", "+00:00"))
        except ValueError:
            continue
        d = t_utc.astimezone(PARIS).date()
        lead = (d - today).days
        if lead < 1 or lead > 7:
            continue

        vals = block.get("values") or block

        def v(*keys: str) -> Any:
            for k in keys:
                if k in vals and vals[k] is not None:
                    return vals[k]
            return None

        tmax = v("temperatureMax")
        tmin = v("temperatureMin")
        tmean = v("temperatureAvg")
        if tmean is None and tmax is not None and tmin is not None:
            tmean = (float(tmax) + float(tmin)) / 2.0

        pp_raw = v("precipitationProbabilityAvg", "precipitationProbabilityMax", "precipitationProbability")
        pp = float(pp_raw) if pp_raw is not None else None

        rain = v("rainAccumulationSum")

        wd = v("windDirectionAvg", "windDirection")
        wc = v("weatherCodeMax", "weatherCode")

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
                "wind_speed_ms": v("windSpeedMax", "windSpeedAvg"),
                "wind_gust_ms": v("windGustMax"),
                "wind_dir_deg": float(wd) if wd is not None else None,
                "precip_prob": pp,
                "precip_amount_mm": rain,
                "cloud_cover_pct": None,
                "weather_code": int(wc) if wc is not None else None,
                "raw": {"source": "tomorrow_io", "index": i},
            }
        )
    rows.sort(key=lambda r: r["lead_days"])
    return rows
