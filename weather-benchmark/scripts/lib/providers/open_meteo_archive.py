"""
Série historique Open-Meteo Archive (sans clé).
https://open-meteo.com/en/docs/historical-weather-api
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from lib.http_util import http_get_json_with_curl_fallback

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def fetch_daily_observations(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    *,
    http_client: httpx.Client | None = None,
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
            "wind_speed_10m_max",
            "wind_direction_10m_dominant",
        ],
        "timezone": "Europe/Paris",
        "windspeed_unit": "ms",
    }
    return http_get_json_with_curl_fallback(ARCHIVE, params, client=http_client)


def observation_rows(
    city_id: int,
    lat: float,
    lon: float,
    start: date,
    end: date,
    source: str = "open_meteo_archive",
    *,
    http_client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    data = fetch_daily_observations(lat, lon, start, end, http_client=http_client)
    daily = data.get("daily") or {}
    times = daily.get("time") or []

    def col(name: str, i: int) -> Any:
        arr = daily.get(name)
        if not arr or i >= len(arr):
            return None
        return arr[i]

    out: list[dict[str, Any]] = []
    for i, day_str in enumerate(times):
        obs_date = date.fromisoformat(day_str)
        tmax = col("temperature_2m_max", i)
        tmin = col("temperature_2m_min", i)
        tmean = col("temperature_2m_mean", i)
        if tmean is None and tmax is not None and tmin is not None:
            tmean = (float(tmax) + float(tmin)) / 2.0
        out.append(
            {
                "city_id": city_id,
                "obs_date": obs_date,
                "temp_max_c": tmax,
                "temp_min_c": tmin,
                "temp_mean_c": tmean,
                "wind_speed_max_ms": col("wind_speed_10m_max", i),
                "wind_dir_deg": col("wind_direction_10m_dominant", i),
                "precip_sum_mm": col("precipitation_sum", i),
                "sunshine_hours": None,
                "source": source,
                "raw": {"archive": "open_meteo"},
            }
        )
    return out
