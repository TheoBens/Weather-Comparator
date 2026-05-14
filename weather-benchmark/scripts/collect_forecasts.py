#!/usr/bin/env python3
"""
Collecte des prévisions et insertion en base.
Pour l’instant : connecteur Open-Meteo (sans clé). Ajouter les autres fournisseurs dans lib/providers/.
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from psycopg.types.json import Json

from lib.db import connection, query_one, query_all
from lib.providers.open_meteo import daily_rows_for_city


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collecte des prévisions météo")
    p.add_argument(
        "--providers",
        nargs="+",
        default=["open_meteo"],
        help="Codes fournisseurs à exécuter (ex: open_meteo)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    issued_at = datetime.now(timezone.utc)

    with connection() as conn:
        cur = conn.cursor()
        total = 0
        cur.execute(
            "INSERT INTO ingest_runs (started_at, source) VALUES (%s, %s) RETURNING id",
            (issued_at, "collect_forecasts.py"),
        )
        run_id = cur.fetchone()["id"]

        for code in args.providers:
            if code != "open_meteo":
                raise SystemExit(f"Fournisseur non implémenté encore: {code}")

            row = query_one(conn, "SELECT id FROM providers WHERE code = %s", (code,))
            if not row:
                raise SystemExit(f"Fournisseur inconnu en base: {code}")
            provider_id = row["id"]

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
            n = 0
            for i, c in enumerate(cities):
                if i:
                    time.sleep(0.5)
                rows = daily_rows_for_city(issued_at, c["id"], c["latitude"], c["longitude"])
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
                    n += 1
                    total += 1
                print(f"  {code} — {c['slug']}: {len(rows)} lignes")

        cur.execute(
            "UPDATE ingest_runs SET finished_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), run_id),
        )
        print(f"Terminé. Run id={run_id}, prévisions insérées={total}")


if __name__ == "__main__":
    main()
