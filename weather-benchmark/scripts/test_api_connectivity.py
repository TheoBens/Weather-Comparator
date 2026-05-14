#!/usr/bin/env python3
"""
Teste une requête minimale par fournisseur météo (Paris) pour valider clés et connectivité.

Usage :
  cd scripts
  pip install -r requirements.txt
  pip install -r requirements-dev.txt   # optionnel (Meteostat, API « grand public » MF)
  cp .env.example .env                  # puis renseigner les clés à tester
  python test_api_connectivity.py
  python test_api_connectivity.py --only open_meteo open_meteo_meteofrance_model
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Callable

import httpx

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lib.config  # noqa: F401 — charge scripts/.env

# Paris centre-ville (aligné sur schema SQL)
LAT, LON = 48.8566, 2.3522


def _summarize_json(data: Any, max_len: int = 180) -> str:
    import json

    s = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return (s[:max_len] + "…") if len(s) > max_len else s


def _run(key: str, fn: Callable[[], dict[str, Any]], only: set[str] | None) -> dict[str, Any]:
    if only is not None and key not in only:
        return {"name": key, "skipped": True, "detail": "filtré par --only"}
    try:
        return fn()
    except Exception as e:
        return {"name": key, "ok": False, "detail": repr(e)}


def test_open_meteo() -> dict[str, Any]:
    r = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LAT,
            "longitude": LON,
            "daily": "temperature_2m_max,precipitation_sum",
            "forecast_days": 3,
            "timezone": "Europe/Paris",
        },
        timeout=30.0,
    )
    r.raise_for_status()
    data = r.json()
    t = (data.get("daily") or {}).get("time") or []
    return {"name": "open_meteo", "ok": True, "http": r.status_code, "detail": f"jours={t}"}


def test_open_meteo_meteofrance_model() -> dict[str, Any]:
    """Modèle MF (AROME/ARPEGE) via Open-Meteo — sans clé Météo-France."""
    r = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LAT,
            "longitude": LON,
            "hourly": "temperature_2m",
            "models": "meteofrance_seamless",
            "forecast_days": 2,
            "timezone": "Europe/Paris",
        },
        timeout=30.0,
    )
    r.raise_for_status()
    data = r.json()
    h = (data.get("hourly") or {}).get("time") or []
    return {
        "name": "open_meteo_meteofrance_model",
        "ok": True,
        "http": r.status_code,
        "detail": f"points horaires={len(h)}",
    }


def test_openweathermap() -> dict[str, Any]:
    key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not key:
        return {"name": "openweathermap", "ok": False, "detail": "OPENWEATHERMAP_API_KEY manquant"}
    r = httpx.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"lat": LAT, "lon": LON, "appid": key, "units": "metric", "cnt": 8},
        timeout=30.0,
    )
    if r.status_code != 200:
        return {"name": "openweathermap", "ok": False, "http": r.status_code, "detail": r.text[:200]}
    data = r.json()
    n = len(data.get("list") or [])
    return {"name": "openweathermap", "ok": True, "http": r.status_code, "detail": f"slots={n}"}


def test_weatherapi() -> dict[str, Any]:
    key = os.getenv("WEATHERAPI_KEY")
    if not key:
        return {"name": "weatherapi", "ok": False, "detail": "WEATHERAPI_KEY manquant"}
    r = httpx.get(
        "https://api.weatherapi.com/v1/forecast.json",
        params={"key": key, "q": f"{LAT},{LON}", "days": 7},
        timeout=30.0,
    )
    if r.status_code != 200:
        return {"name": "weatherapi", "ok": False, "http": r.status_code, "detail": r.text[:200]}
    data = r.json()
    days = len((data.get("forecast") or {}).get("forecastday") or [])
    return {"name": "weatherapi", "ok": True, "http": r.status_code, "detail": f"jours={days}"}


def test_tomorrow_io() -> dict[str, Any]:
    key = os.getenv("TOMORROW_IO_API_KEY")
    if not key:
        return {"name": "tomorrow_io", "ok": False, "detail": "TOMORROW_IO_API_KEY manquant"}
    r = httpx.get(
        "https://api.tomorrow.io/v4/weather/forecast",
        params={
            "location": f"{LAT},{LON}",
            "apikey": key,
            "timesteps": "1d",
        },
        timeout=45.0,
    )
    if r.status_code != 200:
        return {"name": "tomorrow_io", "ok": False, "http": r.status_code, "detail": r.text[:200]}
    data = r.json()
    tlines = data.get("data") or data.get("timelines") or []
    return {"name": "tomorrow_io", "ok": True, "http": r.status_code, "detail": _summarize_json(tlines)}


def test_visual_crossing() -> dict[str, Any]:
    key = os.getenv("VISUAL_CROSSING_API_KEY")
    if not key:
        return {"name": "visual_crossing", "ok": False, "detail": "VISUAL_CROSSING_API_KEY manquant"}
    r = httpx.get(
        "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
        f"{LAT},{LON}/next7days",
        params={"unitGroup": "metric", "key": key, "include": "days"},
        timeout=45.0,
    )
    if r.status_code != 200:
        return {"name": "visual_crossing", "ok": False, "http": r.status_code, "detail": r.text[:200]}
    data = r.json()
    days = len(data.get("days") or [])
    addr = data.get("resolvedAddress", "")
    return {
        "name": "visual_crossing",
        "ok": True,
        "http": r.status_code,
        "detail": f"jours={days} lieu~{addr[:40]}",
    }


def test_foreca() -> dict[str, Any]:
    token = os.getenv("FORECA_API_KEY")
    if not token:
        return {"name": "foreca", "ok": False, "detail": "FORECA_API_KEY manquant"}
    url = f"https://pfa.foreca.com/api/v1/forecast/daily/{LAT},{LON}"
    for label, headers, params in (
        ("Bearer", {"Authorization": f"Bearer {token}"}, {}),
        ("query_token", {}, {"token": token}),
    ):
        r = httpx.get(url, headers=headers, params=params, timeout=45.0)
        if r.status_code == 200:
            data = r.json()
            return {
                "name": "foreca",
                "ok": True,
                "http": r.status_code,
                "detail": f"auth={label} {_summarize_json(data, 120)}",
            }
    return {"name": "foreca", "ok": False, "http": r.status_code, "detail": r.text[:250]}


def test_meteostat() -> dict[str, Any]:
    """Meteostat 2.x : `daily(Point, start, end)` + `fetch()` — pas d’ancienne classe `Daily`."""
    try:
        from datetime import date, timedelta

        from meteostat import Point
        from meteostat import daily
    except ImportError as e:
        return {
            "name": "meteostat",
            "ok": False,
            "detail": f"import: {e!r} (pip install meteostat)",
        }
    end = date.today()
    start = end - timedelta(days=7)
    try:
        ts = daily(Point(LAT, LON), start, end)
        ts.fetch()
    except Exception as e:
        return {"name": "meteostat", "ok": False, "detail": repr(e)}
    # Données vides possibles (réseau / offre), le test valide surtout l’appel.
    empty = getattr(ts, "empty", True)
    n = ts.count() if callable(getattr(ts, "count", None)) else 0
    return {
        "name": "meteostat",
        "ok": True,
        "detail": f"TimeSeries OK empty={empty} count={n}",
    }


def test_meteofrance_grand_public() -> dict[str, Any]:
    """API Python « meteofrance-api » (prévisions grand public), distincte du portail Open Data."""
    try:
        from meteofrance_api import MeteoFranceClient
    except ImportError:
        return {
            "name": "meteofrance_grand_public",
            "ok": False,
            "detail": "pip install meteofrance-api (voir requirements-dev.txt)",
        }
    client = MeteoFranceClient()
    f = client.get_forecast(LAT, LON, language="fr")
    daily = getattr(f, "daily_forecast", None) or []
    return {
        "name": "meteofrance_grand_public",
        "ok": True,
        "detail": f"previsions journalieres~{len(daily)} (client Python MF)",
    }


def test_meteofrance_open_data_portail() -> dict[str, Any]:
    """
    Portail Open Data MF : renseigne METEO_FRANCE_API_URL (URL de ressource du portail)
    + METEO_FRANCE_API_KEY si ton abonnement l’exige.
    """
    url = os.getenv("METEO_FRANCE_API_URL")
    key = os.getenv("METEO_FRANCE_API_KEY")
    if not url:
        return {
            "name": "meteofrance_open_data_portail",
            "ok": False,
            "detail": "METEO_FRANCE_API_URL non défini (portail MF)",
        }
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    r = httpx.get(url, headers=headers, timeout=45.0)
    if r.status_code != 200:
        return {
            "name": "meteofrance_open_data_portail",
            "ok": False,
            "http": r.status_code,
            "detail": r.text[:200],
        }
    return {"name": "meteofrance_open_data_portail", "ok": True, "http": r.status_code, "detail": "réponse OK"}


TESTS: list[Callable[[], dict[str, Any]]] = [
    test_open_meteo,
    test_open_meteo_meteofrance_model,
    test_openweathermap,
    test_weatherapi,
    test_tomorrow_io,
    test_visual_crossing,
    test_foreca,
    test_meteostat,
    test_meteofrance_grand_public,
    test_meteofrance_open_data_portail,
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--only",
        nargs="*",
        help="Noms : open_meteo, open_meteo_meteofrance_model, openweathermap, weatherapi, …",
    )
    args = p.parse_args()
    only = set(args.only) if args.only else None

    results: list[dict[str, Any]] = []
    for fn in TESTS:
        key = fn.__name__.replace("test_", "")
        results.append(_run(key, fn, only))

    print("\nRésultats (Paris 48.8566, 2.3522)\n" + "-" * 72)
    for row in results:
        if row.get("skipped"):
            print(f"  {row['name']:<35} IGNORÉ  {row['detail']}")
            continue
        status = "OK" if row.get("ok") else "ECHEC"
        http = row.get("http", "")
        http_s = f" HTTP {http}" if http else ""
        name = row.get("name", "?")
        print(f"  {name:<35} {status:6}{http_s}  {row.get('detail', '')}")
    print("-" * 72 + "\n")


if __name__ == "__main__":
    main()
