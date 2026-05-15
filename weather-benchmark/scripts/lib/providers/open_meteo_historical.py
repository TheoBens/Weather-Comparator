"""
Archive « historical forecast » Open-Meteo (sans clé).

https://open-meteo.com/en/docs/historical-forecast-api

Produit une ligne par jour calendaire Paris dans [start, end], avec lead_days = 1, pour permettre
le calcul des scores en local sans attendre plusieurs exécutions quotidiennes. Les valeurs sont une
construction continue à partir des mises à jour du modèle, pas une relance exacte d’un run passé à
chaque horizon.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx

from lib.http_util import httpx_get

HISTORICAL_FORECAST = "https://historical-forecast-api.open-meteo.com/v1/forecast"


def fetch_historical_daily(
    latitude: float,
    longitude: float,
    *,
    start: date,
    end: date,
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "precipitation_probability_max",
            "windspeed_10m_max",
            "winddirection_10m_dominant",
            "weathercode",
        ],
        "timezone": "Europe/Paris",
        "windspeed_unit": "ms",
    }
    r = httpx_get(HISTORICAL_FORECAST, params=params, timeout=httpx.Timeout(120.0, connect=45.0))
    return r.json()


def historical_daily_rows_for_city(
    city_id: int,
    lat: float,
    lon: float,
    start: date,
    end: date,
    *,
    lead_days: int = 1,
) -> list[dict[str, Any]]:
    """Une ligne par jour d entre start et end (dates Paris dans la réponse API)."""
    if lead_days < 1 or lead_days > 7:
        raise ValueError("lead_days doit être entre 1 et 7")
    data = fetch_historical_daily(lat, lon, start=start, end=end)
    daily = data.get("daily") or {}
    time_list = daily.get("time") or []
    rows: list[dict[str, Any]] = []

    def col(name: str, i: int) -> Any:
        arr = daily.get(name)
        if not arr or i >= len(arr):
            return None
        return arr[i]

    for i, day_str in enumerate(time_list):
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            continue
        if d < start or d > end:
            continue
        tmax = col("temperature_2m_max", i)
        tmin = col("temperature_2m_min", i)
        tmean = col("temperature_2m_mean", i)
        if tmean is None and tmax is not None and tmin is not None:
            tmean = (float(tmax) + float(tmin)) / 2.0
        pp = col("precipitation_probability_max", i)
        if pp is not None:
            pp = float(pp)
        issued_day = d - timedelta(days=lead_days)
        issued_at = datetime.combine(issued_day, time(12, 0, 0), tzinfo=timezone.utc)
        valid_time = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc)
        rows.append(
            {
                "city_id": city_id,
                "issued_at": issued_at,
                "valid_time": valid_time,
                "lead_days": lead_days,
                "time_step": "daily",
                "temp_max_c": tmax,
                "temp_min_c": tmin,
                "temp_mean_c": tmean,
                "wind_speed_ms": col("windspeed_10m_max", i),
                "wind_gust_ms": None,
                "wind_dir_deg": col("winddirection_10m_dominant", i),
                "precip_prob": pp,
                "precip_amount_mm": col("precipitation_sum", i),
                "cloud_cover_pct": None,
                "weather_code": int(col("weathercode", i)) if col("weathercode", i) is not None else None,
                "raw": {"source": "open_meteo_historical_forecast", "daily_index": i},
            }
        )
    return rows
