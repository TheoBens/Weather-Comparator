"""
Prévisions OpenWeatherMap (API 5 jours / pas 3h, agrégation journalière fuseau Paris).
https://openweathermap.org/forecast5
"""
from __future__ import annotations

import math
import os
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from lib.http_util import httpx_get

PARIS = ZoneInfo("Europe/Paris")
OWM_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"


def fetch_forecast_5d(latitude: float, longitude: float) -> dict[str, Any]:
    key = (os.getenv("OPENWEATHERMAP_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "OPENWEATHERMAP_API_KEY manquant (.env). "
            "Crée une clé sur https://openweathermap.org/api"
        )
    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": key,
        "units": "metric",
    }
    try:
        r = httpx_get(OWM_FORECAST, params=params, timeout=httpx.Timeout(90.0, connect=45.0))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise RuntimeError(
                "OpenWeatherMap refuse encore la clé (401). Après inscription, ils indiquent souvent "
                "une activation sous quelques heures avant que 2.5/forecast réponde. "
                "En attendant : lance uniquement les autres fournisseurs ou réessaie plus tard. "
                "Ensuite vérifie : OPENWEATHERMAP_API_KEY dans weather-benchmark/scripts/.env, "
                "email de compte validé, et produits gratuits Forecast actifs dans le tableau de bord."
            ) from e
        raise
    return r.json()


def daily_rows_for_city(
    issued_at: datetime,
    city_id: int,
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    data = fetch_forecast_5d(lat, lon)
    today = datetime.now(PARIS).date()

    buckets: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for item in data.get("list") or []:
        ts = item.get("dt")
        if ts is None:
            continue
        utc = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        loc_d = utc.astimezone(PARIS).date()
        buckets[loc_d].append(item)

    rows: list[dict[str, Any]] = []
    sorted_days = sorted(buckets.keys())
    for fi, d in enumerate(sorted_days):
        lead = (d - today).days
        if lead < 1 or lead > 7:
            continue
        items = buckets[d]
        if not items:
            continue
        mains = [x["main"] for x in items if isinstance(x.get("main"), dict)]
        temps = [float(m["temp"]) for m in mains if m.get("temp") is not None]
        tmins_m = [
            float(m["temp_min"])
            for m in mains
            if m.get("temp_min") is not None and m.get("temp_max") is not None
        ]
        tmaxs_m = [
            float(m["temp_max"]) for m in mains if m.get("temp_min") is not None and m.get("temp_max") is not None
        ]
        tmax_final = max(tmaxs_m) if tmaxs_m else (max(temps) if temps else None)
        tmin_final = min(tmins_m) if tmins_m else (min(temps) if temps else None)
        tmean = sum(temps) / len(temps) if temps else None
        winds = []
        wind_degs = []
        for x in items:
            w = x.get("wind") or {}
            if w.get("speed") is not None:
                try:
                    winds.append(float(w["speed"]))
                except (TypeError, ValueError):
                    pass
            if w.get("deg") is not None:
                try:
                    wind_degs.append(float(w["deg"]))
                except (TypeError, ValueError):
                    pass
        wspeed = max(winds) if winds else None
        # direction moyenne circulaire simplifiée (ok pour indice agrégé)
        wdeg = None
        if wind_degs:
            sx = sum(math.sin(math.radians(v)) for v in wind_degs)
            cx = sum(math.cos(math.radians(v)) for v in wind_degs)
            if cx or sx:
                wdeg = (math.degrees(math.atan2(sx, cx)) + 360.0) % 360.0

        rain_mm = 0.0
        for x in items:
            for key in ("rain", "snow"):
                block = x.get(key)
                if isinstance(block, dict):
                    v = block.get("3h")
                    if v is not None:
                        try:
                            rain_mm += float(v)
                        except (TypeError, ValueError):
                            pass

        probs = []
        for x in items:
            pop = x.get("pop")
            if pop is not None:
                try:
                    probs.append(float(pop))
                except (TypeError, ValueError):
                    pass
        pp = max(probs) * 100.0 if probs else None

        wcode = None
        first_w = items[0].get("weather")
        if isinstance(first_w, list) and first_w:
            cid = first_w[0].get("id")
            if cid is not None:
                wcode = int(cid)

        rows.append(
            {
                "city_id": city_id,
                "issued_at": issued_at,
                "valid_time": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                "lead_days": lead,
                "time_step": "daily",
                "temp_max_c": tmax_final,
                "temp_min_c": tmin_final,
                "temp_mean_c": tmean,
                "wind_speed_ms": wspeed,
                "wind_gust_ms": None,
                "wind_dir_deg": wdeg,
                "precip_prob": pp,
                "precip_amount_mm": rain_mm,
                "cloud_cover_pct": None,
                "weather_code": wcode,
                "raw": {
                    "source": "openweathermap",
                    "n_steps": len(items),
                    "forecast_index": fi,
                },
            }
        )

    rows.sort(key=lambda r: r["lead_days"])
    return rows
