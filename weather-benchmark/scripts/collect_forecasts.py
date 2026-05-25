#!/usr/bin/env python3
"""
Collecte des previsions et insertion en base.
Fournisseurs : open_meteo, meteo_france (Open-Meteo MF, sans cle), weatherapi,
openweathermap, tomorrow_io, visual_crossing (cles optionnelles : sautes si absentes).
Meteostat : pas de previsions multi-jours dans ce depot (observations).
"""
from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone

from psycopg.types.json import Json

from lib.db import connection, query_one, query_all
from lib.providers.meteo_france import daily_rows_for_city as meteo_france_daily_rows
from lib.providers.open_meteo import daily_rows_for_city as open_meteo_daily_rows
from lib.providers.openweathermap import daily_rows_for_city as openweathermap_daily_rows
from lib.providers.tomorrow_io import daily_rows_for_city as tomorrow_io_daily_rows
from lib.providers.visual_crossing import daily_rows_for_city as visual_crossing_daily_rows
from lib.providers.weatherapi import daily_rows_for_city as weatherapi_daily_rows

ForecastCollector = Callable[[datetime, int, float, float], list]

COLLECTORS: dict[str, ForecastCollector] = {
    "open_meteo": open_meteo_daily_rows,
    "meteo_france": meteo_france_daily_rows,
    "weatherapi": weatherapi_daily_rows,
    "openweathermap": openweathermap_daily_rows,
    "tomorrow_io": tomorrow_io_daily_rows,
    "visual_crossing": visual_crossing_daily_rows,
}

# Défaut = tout le monde (sans clé = saute silencieusement, comme dans le workflow GitHub)
DEFAULT_PROVIDER_CODES: tuple[str, ...] = tuple(COLLECTORS.keys())

PROVIDER_REQUIRES_ENV: dict[str, tuple[str, ...]] = {
    "weatherapi": ("WEATHERAPI_KEY", "WEATHERAPI_API_KEY"),
    "openweathermap": ("OPENWEATHERMAP_API_KEY",),
    "tomorrow_io": ("TOMORROW_IO_API_KEY",),
    "visual_crossing": ("VISUAL_CROSSING_API_KEY",),
}


def provider_env_missing(code: str) -> bool:
    keys = PROVIDER_REQUIRES_ENV.get(code)
    if not keys:
        return False
    return not any((os.getenv(k) or "").strip() for k in keys)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collecte des prev meteo")
    p.add_argument(
        "--providers",
        nargs="+",
        default=list(DEFAULT_PROVIDER_CODES),
        help=(
            "Codes (défaut : tous). Sans clé pour un API payant/free tier, ce fournisseur est ignoré."
            "Liste : "
            + ", ".join(DEFAULT_PROVIDER_CODES)
        ),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    issued_at = datetime.now(timezone.utc)

    for code in args.providers:
        if code not in COLLECTORS:
            raise SystemExit(
                f"Fournisseur inconnu ou non gere: {code} "
                "(meteostat n'a pas de connecteur prev ici)."
            )

    with connection() as conn:
        cur = conn.cursor()
        total = 0
        cur.execute(
            "INSERT INTO ingest_runs (started_at, source) VALUES (%s, %s) RETURNING id",
            (issued_at, "collect_forecasts.py"),
        )
        run_id = cur.fetchone()["id"]

        cities = query_all(conn, "SELECT id, latitude, longitude, slug FROM cities ORDER BY id")
        insert_sql = """
            INSERT INTO forecasts (
              ingest_run_id, provider_id, city_id, issued_at, valid_time, lead_days,
              time_step, temp_max_c, temp_min_c, temp_mean_c, wind_speed_ms, wind_gust_ms,
              wind_dir_deg, precip_prob, precip_amount_mm, cloud_cover_pct, weather_code, raw
            ) VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

        for code in args.providers:
            if provider_env_missing(code):
                print(f"  {code} - cle API absente, saute")
                continue

            collector = COLLECTORS[code]
            row = query_one(conn, "SELECT id FROM providers WHERE code = %s", (code,))
            if not row:
                raise SystemExit(f"Fournisseur inconnu en base (schema?): {code}")
            provider_id = row["id"]

            savepoint = f"s_collect_{code}"
            cur.execute(f"SAVEPOINT {savepoint}")
            try:
                for i, c in enumerate(cities):
                    if i:
                        time.sleep(0.6)
                    rows = collector(issued_at, c["id"], c["latitude"], c["longitude"])
                    for r in rows:
                        cur.execute(
                            insert_sql,
                            (
                                run_id,
                                provider_id,
                                r["city_id"],
                                r["issued_at"],
                                r["valid_time"],
                                r["lead_days"],
                                r["time_step"],
                                r["temp_max_c"],
                                r["temp_min_c"],
                                r["temp_mean_c"],
                                r["wind_speed_ms"],
                                r["wind_gust_ms"],
                                r["wind_dir_deg"],
                                r["precip_prob"],
                                r["precip_amount_mm"],
                                r["cloud_cover_pct"],
                                r["weather_code"],
                                Json(r["raw"]),
                            ),
                        )
                        total += 1
                    print(f"  {code} - {c['slug']}: {len(rows)} lignes")
                cur.execute(f"RELEASE SAVEPOINT {savepoint}")
            except Exception as e:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                print(f"  {code} - ECHEC (reste du run continue): {e}")

        cur.execute(
            "UPDATE ingest_runs SET finished_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), run_id),
        )
        print(f"Termine. Run id={run_id}, previsions inserees={total}")


if __name__ == "__main__":
    main()
