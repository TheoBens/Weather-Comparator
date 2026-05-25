#!/usr/bin/env python3
"""
Scores « equitables » : memes couples (ville, jour d observation) pour tous les fournisseurs
demandes — garde uniquement les jours ou chaque API a bien une ligne de prevision (derniere emission).

Insere forecast_scores avec score_window_* = [min(jour), max(jour)] parmi les jours ou tous les fournisseurs
ont une prevision (souvent plus etroit que la fenetre demandee en ligne de commande).
Le dashboard choisit la derniere score_window_end puis le score_window_start le plus recent parmi ces fins.

Usage :
  cd weather-benchmark/scripts
  python compute_fair_scores.py --days 10
  python compute_fair_scores.py --days 14 --providers open_meteo weatherapi openweathermap
"""
from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from datetime import date, timedelta

import numpy as np

from lib.db import connection, query_all

RAIN_THRESHOLD_MM = 0.1

DEFAULT_PROVIDER_CODES = (
    "open_meteo",
    "meteo_france",
    "weatherapi",
    "openweathermap",
    "tomorrow_io",
    "visual_crossing",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scores comparatif equitatif (couverture complete)")
    p.add_argument(
        "--providers",
        nargs="+",
        default=list(DEFAULT_PROVIDER_CODES),
        help="Codes fournisseurs a inclure tous ensemble (sinon aucun groupe complet)",
    )
    p.add_argument(
        "--days",
        type=int,
        default=14,
        help="Fenetre d observations : de (hier - days + 1) a hier inclusivement",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=args.days - 1)
    codes = tuple(dict.fromkeys(args.providers))

    sql_lookup = """SELECT id, code FROM providers WHERE code = ANY(%s)"""
    with connection() as conn:
        prov_rows = query_all(conn, sql_lookup, (list(codes),))
        by_code = {r["code"]: r["id"] for r in prov_rows}
    missing = [c for c in codes if c not in by_code]
    if missing:
        raise SystemExit(f"Codes inconnus en base : {missing}")
    pids = [by_code[c] for c in codes]
    n_prev = len(pids)

    sql_pairs = """
    WITH lf AS (
      SELECT DISTINCT ON (f.provider_id, f.city_id, (f.valid_time AT TIME ZONE 'Europe/Paris')::date)
        f.provider_id,
        f.city_id,
        f.lead_days,
        (f.valid_time AT TIME ZONE 'Europe/Paris')::date AS target_day,
        f.temp_mean_c AS f_temp,
        f.wind_speed_ms AS f_wind,
        f.precip_amount_mm AS f_rain,
        f.precip_prob AS f_prob
      FROM forecasts f
      WHERE f.provider_id = ANY(%s)
        AND (f.valid_time AT TIME ZONE 'Europe/Paris')::date BETWEEN %s AND %s
      ORDER BY f.provider_id, f.city_id, (f.valid_time AT TIME ZONE 'Europe/Paris')::date,
               f.issued_at DESC
    ),
    joined AS (
      SELECT
        lf.provider_id,
        p.code AS provider_code,
        lf.city_id,
        c.slug AS city_slug,
        lf.lead_days,
        lf.target_day,
        lf.f_temp,
        lf.f_wind,
        lf.f_rain,
        lf.f_prob,
        o.temp_mean_c AS o_temp,
        o.wind_speed_max_ms AS o_wind,
        o.precip_sum_mm AS o_rain
      FROM lf
      JOIN observations o
        ON o.city_id = lf.city_id
       AND o.source = 'open_meteo_archive'
       AND o.obs_date = lf.target_day
      JOIN providers p ON p.id = lf.provider_id
      JOIN cities c ON c.id = lf.city_id
      WHERE lf.target_day BETWEEN %s AND %s
        AND lf.f_temp IS NOT NULL
        AND o.temp_mean_c IS NOT NULL
    ),
    coverage AS (
      SELECT city_id, target_day AS obs_date, COUNT(DISTINCT provider_id)::int AS n_prov
      FROM joined
      GROUP BY city_id, target_day
    )
    SELECT j.*
    FROM joined j
    JOIN coverage cov
      ON cov.city_id = j.city_id AND cov.obs_date = j.target_day AND cov.n_prov = %s
    ORDER BY j.provider_code, j.city_slug, j.lead_days
    """

    with connection() as conn:
        rows = query_all(
            conn,
            sql_pairs,
            (pids, start, end, start, end, n_prev),
        )

    if not rows:
        print(
            "Aucun jour avec couverture complete pour tous les fournisseurs demandes "
            f"sur {start} -> {end}."
        )
        print("  Reduction : nombre de providers, augmenter --days, ou poursuivre la collecte quotidienne.")
        return

    pair_counts = Counter(r["provider_code"] for r in rows)
    pairs_per_day_city: dict[tuple[int, date], set[str]] = defaultdict(set)
    for r in rows:
        pairs_per_day_city[(r["city_id"], r["target_day"])].add(r["provider_code"])
    n_city_days = len(pairs_per_day_city)
    print(
        f"Fenetre requise {start} -> {end}. Cellules ville x jour completes ({n_prev} APIs) : {n_city_days}."
    )
    print("Lignes prevision x obs par fournisseur (sur ce jeu complet):")
    for code, n in sorted(pair_counts.items()):
        print(f"  {code}: {n}")

    targets = [r["target_day"] for r in rows]
    eff_start = min(targets)
    eff_end = max(targets)
    print(
        f"Fenetre persistee forecast_scores : {eff_start} -> {eff_end} "
        "(min/max des jours d observation inclus)."
    )

    groups: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["provider_id"], r["city_id"], r["lead_days"])
        groups[key].append(dict(r))

    with connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM forecast_scores
            WHERE score_window_start = %s AND score_window_end = %s
            """,
            (eff_start, eff_end),
        )
        insert_sql = """
        INSERT INTO forecast_scores (
          provider_id, city_id, horizon_days,
          score_window_start, score_window_end,
          n_samples, mae_temp_c, rmse_temp_c, mae_wind_ms,
          rain_binary_accuracy, rain_mae_mm, precip_prob_brier
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for (pid, cid, lead), items in sorted(groups.items()):
            f_temp = np.array([x["f_temp"] for x in items], dtype=float)
            o_temp = np.array([x["o_temp"] for x in items], dtype=float)
            err_t = f_temp - o_temp
            mae_t = float(np.mean(np.abs(err_t)))
            rmse_t = float(math.sqrt(np.mean(err_t**2)))

            fw = [x["f_wind"] for x in items]
            ow = [x["o_wind"] for x in items]
            wind_pairs = [(float(a), float(b)) for a, b in zip(fw, ow) if a is not None and b is not None]
            mae_w = (
                float(np.mean(np.abs(np.array([a - b for a, b in wind_pairs])))) if wind_pairs else None
            )

            fr = [x["f_rain"] for x in items]
            o_rain = [x["o_rain"] for x in items]
            rain_pair = [
                (float(a) if a is not None else 0.0, float(b) if b is not None else 0.0)
                for a, b in zip(fr, o_rain)
            ]
            acc_bits = []
            for a, b in rain_pair:
                pred = a > RAIN_THRESHOLD_MM
                act = b > RAIN_THRESHOLD_MM
                acc_bits.append(1.0 if pred == act else 0.0)
            rain_acc = float(np.mean(acc_bits)) if acc_bits else None
            rain_mae = float(np.mean(np.abs(np.array([a - b for a, b in rain_pair])))) if rain_pair else None

            brier = None
            brier_pairs = [
                (float(x["f_prob"]), float(x["o_rain"]) if x["o_rain"] is not None else 0.0)
                for x in items
                if x["f_prob"] is not None
            ]
            if brier_pairs:
                brier_sum = 0.0
                for p_raw, obs_r in brier_pairs:
                    o_bin = 1.0 if obs_r > RAIN_THRESHOLD_MM else 0.0
                    pr = p_raw / 100.0 if p_raw > 1.0 else p_raw
                    pr = min(max(pr, 0.0), 1.0)
                    brier_sum += (pr - o_bin) ** 2
                brier = brier_sum / len(brier_pairs)

            cur.execute(
                insert_sql,
                (
                    pid,
                    cid,
                    lead,
                    eff_start,
                    eff_end,
                    len(items),
                    mae_t,
                    rmse_t,
                    mae_w,
                    rain_acc,
                    rain_mae,
                    brier,
                ),
            )

        print(
            f"Scores equitables inseres : {len(groups)} groupes. "
            f"Fenetre {eff_start} -> {eff_end}. Recharge le dashboard."
        )


if __name__ == "__main__":
    main()
