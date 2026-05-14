"""
Prévisions Open-Meteo (sans clé API).
https://open-meteo.com/en/docs
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

PARIS = ZoneInfo("Europe/Paris")

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"


def fetch_daily_forecast(
    latitude: float,
    longitude: float,
    *,
    forecast_days: int = 8,
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
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
        "forecast_days": forecast_days,
        "timezone": "Europe/Paris",
        "windspeed_unit": "ms",
    }
    r = httpx.get(OPEN_METEO_FORECAST, params=params, timeout=60.0)
    r.raise_for_status()
    return r.json()


def daily_rows_for_city(
    issued_at: datetime,
    city_id: int,
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    """Transforme la réponse API en lignes prêtes à insérer (lead_days 1..7)."""
    data = fetch_daily_forecast(lat, lon, forecast_days=8)
    daily = data.get("daily") or {}
    time_list = daily.get("time") or []
    rows: list[dict[str, Any]] = []
    today = datetime.now(PARIS).date()

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
        lead = (d - today).days
        if lead < 1 or lead > 7:
            continue
        tmax = col("temperature_2m_max", i)
        tmin = col("temperature_2m_min", i)
        tmean = col("temperature_2m_mean", i)
        if tmean is None and tmax is not None and tmin is not None:
            tmean = (float(tmax) + float(tmin)) / 2.0
        pp = col("precipitation_probability_max", i)
        if pp is not None:
            pp = float(pp)
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
                "wind_speed_ms": col("windspeed_10m_max", i),
                "wind_gust_ms": None,
                "wind_dir_deg": col("winddirection_10m_dominant", i),
                "precip_prob": pp,
                "precip_amount_mm": col("precipitation_sum", i),
                "cloud_cover_pct": None,
                "weather_code": int(col("weathercode", i)) if col("weathercode", i) is not None else None,
                "raw": {"source": "open_meteo", "daily_index": i},
            }
        )
    return rows
