"""
Série historique Open-Meteo Archive (sans clé).
https://open-meteo.com/en/docs/historical-weather-api

Les requêtes sont découpées en plusieurs fenêtres courtes : moins de risque de timeout sur les
runners CI (GitHub Actions) vers archive-api.open-meteo.com.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from lib.http_util import http_get_json_with_curl_fallback

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

# Fenêtres courtes : une seule grosse requête multi-villes × 14 jours peut expirer en connect.
_DEFAULT_CHUNK_DAYS = 5


def _daily_params(latitude: float, longitude: float, start: date, end: date) -> dict[str, Any]:
    return {
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


def _merge_archive_payloads(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Concatène les blocs ``daily.*`` dans l'ordre des chunks (dates croissantes)."""
    if not parts:
        return {}
    if len(parts) == 1:
        return parts[0]

    merged: dict[str, Any] = dict(parts[0])
    keys: set[str] = set()
    for p in parts:
        d = p.get("daily") or {}
        keys.update(d.keys())

    merged_daily: dict[str, Any] = {}
    for key in sorted(keys):
        vals: list[Any] = []
        for p in parts:
            daily = p.get("daily") or {}
            chunk = daily.get(key)
            if isinstance(chunk, list):
                vals.extend(chunk)
            elif chunk is not None:
                vals.append(chunk)
        merged_daily[key] = vals
    merged["daily"] = merged_daily
    return merged


def _fetch_one_span(
    lat: float,
    lon: float,
    start: date,
    end: date,
    *,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    return http_get_json_with_curl_fallback(
        ARCHIVE,
        _daily_params(lat, lon, start, end),
        client=http_client,
    )


def fetch_daily_observations(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    *,
    http_client: httpx.Client | None = None,
    chunk_days: int = _DEFAULT_CHUNK_DAYS,
) -> dict[str, Any]:
    if end < start:
        return {}

    span_days = (end - start).days + 1
    if span_days <= chunk_days:
        return _fetch_one_span(latitude, longitude, start, end, http_client=http_client)

    chunks: list[dict[str, Any]] = []
    cur = start
    while cur <= end:
        sub_end = min(cur + timedelta(days=chunk_days - 1), end)
        chunks.append(_fetch_one_span(latitude, longitude, cur, sub_end, http_client=http_client))
        cur = sub_end + timedelta(days=1)
    return _merge_archive_payloads(chunks)


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
                "raw": {"archive": "open-meteo"},
            }
        )
    return out
