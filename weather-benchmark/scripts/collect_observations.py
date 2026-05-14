#!/usr/bin/env python3
"""
Récupération des observations passées (vérité terrain) pour calibrer les scores.
Source par défaut : Open-Meteo Archive (sans clé).
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

from psycopg.types.json import Json

from lib.db import connection, query_all
from lib.http_util import archive_client
from lib.providers.open_meteo_archive import observation_rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collecte des observations agrégées jour/jour")
    p.add_argument("--days", type=int, default=14, help="Nombre de jours en arrière à inclure")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    end = date.today()
    start = end - timedelta(days=args.days)

    with connection() as conn:
        cur = conn.cursor()
        cities = query_all(conn, "SELECT id, latitude, longitude, slug FROM cities ORDER BY id")
        sql = """
        INSERT INTO observations (
          city_id, obs_date, temp_max_c, temp_min_c, temp_mean_c,
          wind_speed_max_ms, wind_dir_deg, precip_sum_mm, sunshine_hours, source, raw
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (city_id, obs_date, source) DO UPDATE SET
          temp_max_c = EXCLUDED.temp_max_c,
          temp_min_c = EXCLUDED.temp_min_c,
          temp_mean_c = EXCLUDED.temp_mean_c,
          wind_speed_max_ms = EXCLUDED.wind_speed_max_ms,
          wind_dir_deg = EXCLUDED.wind_dir_deg,
          precip_sum_mm = EXCLUDED.precip_sum_mm,
          sunshine_hours = EXCLUDED.sunshine_hours,
          raw = EXCLUDED.raw
        """
        total = 0
        with archive_client() as http_client:
            for i, c in enumerate(cities):
                if i:
                    time.sleep(1.5)
                rows = observation_rows(
                    c["id"],
                    c["latitude"],
                    c["longitude"],
                    start,
                    end,
                    http_client=http_client,
                )
                for r in rows:
                    cur.execute(
                        sql,
                        (
                            r["city_id"],
                            r["obs_date"],
                            r["temp_max_c"],
                            r["temp_min_c"],
                            r["temp_mean_c"],
                            r["wind_speed_max_ms"],
                            r["wind_dir_deg"],
                            r["precip_sum_mm"],
                            r["sunshine_hours"],
                            r["source"],
                            Json(r["raw"]),
                        ),
                    )
                    total += 1
                print(f"  {c['slug']}: {len(rows)} jours")
        print(f"Observations écrites (lignes traitées): {total}")


if __name__ == "__main__":
    main()
