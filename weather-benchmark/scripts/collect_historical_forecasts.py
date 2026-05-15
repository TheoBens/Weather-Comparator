#!/usr/bin/env python3
"""
Backfill de prévisions « passées » via l’API Historical Forecast Open-Meteo.

Pourquoi : collect_forecasts.py n’insère que des valid_time futurs (J+1…J+7), donc compute_scores
ne trouve aucune paire avec les observations après un premier run local.

Ré-exécuter ce script écrase les prévisions précédentes issues du même fichier (via ingest_runs.source).
Les runs collect_forecasts.py (source différente) ne sont pas touchés.
"""
from __future__ import annotations

import argparse
import time
from datetime import date, datetime, timedelta, timezone

from psycopg.types.json import Json

from lib.db import connection, query_one, query_all
from lib.providers.open_meteo_historical import historical_daily_rows_for_city

RUN_SOURCE = "collect_historical_forecasts.py"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill prévisions historiques (scores en local)")
    p.add_argument(
        "--providers",
        nargs="+",
        default=["open_meteo"],
        help="Codes fournisseurs cibles",
    )
    p.add_argument(
        "--days",
        type=int,
        default=45,
        help="Nombre de jours civils inclus se terminant à la veille (UTC-calendrier Paris via API)",
    )
    p.add_argument(
        "--lead-days",
        type=int,
        default=1,
        help="Horizon enregistré (1–7). Par défaut 1 (aligné série historique agrégée).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=args.days - 1)
    if start > end:
        raise SystemExit("Fenêtre de dates invalide")

    issued_at = datetime.now(timezone.utc)

    with connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM ingest_runs WHERE source = %s", (RUN_SOURCE,))
        old_run_ids = [r["id"] for r in cur.fetchall()]
        if old_run_ids:
            cur.execute("DELETE FROM forecasts WHERE ingest_run_id = ANY(%s)", (old_run_ids,))
            cur.execute("DELETE FROM ingest_runs WHERE id = ANY(%s)", (old_run_ids,))

        cur.execute(
            "INSERT INTO ingest_runs (started_at, source) VALUES (%s, %s) RETURNING id",
            (issued_at, RUN_SOURCE),
        )
        run_id = cur.fetchone()["id"]

        for code in args.providers:
            if code != "open_meteo":
                raise SystemExit(f"Fournisseur non supporté encore: {code}")
            prow = query_one(conn, "SELECT id FROM providers WHERE code = %s", (code,))
            if not prow:
                raise SystemExit(f"Fournisseur inconnu en base: {code}")
            provider_id = prow["id"]

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
            total = 0
            for i, c in enumerate(cities):
                if i:
                    time.sleep(1.2)
                rows = historical_daily_rows_for_city(
                    c["id"],
                    c["latitude"],
                    c["longitude"],
                    start,
                    end,
                    lead_days=args.lead_days,
                )
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
                print(f"  {code} - {c['slug']}: {len(rows)} jours ({start} -> {end})")

        cur.execute(
            "UPDATE ingest_runs SET finished_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), run_id),
        )
        print(f"Termine. Run id={run_id}, lignes inserees={total}, fenetre {start} -> {end}")


if __name__ == "__main__":
    main()
