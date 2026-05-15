"""
Visual Crossing Timeline (clé API gratuite / crédits).
https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from lib.http_util import httpx_get

PARIS = ZoneInfo("Europe/Paris")
BASE = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"


def fetch_timeline(latitude: float, longitude: float) -> dict[str, Any]:
    key = (os.getenv("VISUAL_CROSSING_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "VISUAL_CROSSING_API_KEY manquant (.env). Creer un compte sur https://www.visualcrossing.com/"
        )
    loc = f"{latitude:.6f},{longitude:.6f}"
    url = f"{BASE}/{loc}"
    params = {
        "key": key,
        "unitGroup": "metric",
        "include": "days",
    }
    r = httpx_get(url, params=params, timeout=httpx.Timeout(90.0, connect=45.0))
    return r.json()


def daily_rows_for_city(
    issued_at: datetime,
    city_id: int,
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    data = fetch_timeline(lat, lon)
    today = datetime.now(PARIS).date()
    rows: list[dict[str, Any]] = []
    days = data.get("days") or []
    for i, day in enumerate(days):
        dt_s = day.get("datetime")
        if not dt_s:
            continue
        try:
            d = date.fromisoformat(str(dt_s)[:10])
        except ValueError:
            continue
        lead = (d - today).days
        if lead < 1 or lead > 7:
            continue
        tmax = day.get("tempmax")
        tmin = day.get("tempmin")
        tmean = day.get("temp")
        if tmean is None and tmax is not None and tmin is not None:
            tmean = (float(tmax) + float(tmin)) / 2.0
        pp = day.get("precipprob")
        if pp is not None:
            pp = float(pp)
        icon = day.get("icon")
        wc = None
        if isinstance(icon, str) and icon.isdigit():
            wc = int(icon)
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
                "wind_speed_ms": day.get("windspeed"),
                "wind_gust_ms": day.get("windgust"),
                "wind_dir_deg": float(day["winddir"]) if day.get("winddir") is not None else None,
                "precip_prob": pp,
                "precip_amount_mm": day.get("precip"),
                "cloud_cover_pct": None,
                "weather_code": wc,
                "raw": {"source": "visual_crossing", "index": i},
            }
        )
    return rows
