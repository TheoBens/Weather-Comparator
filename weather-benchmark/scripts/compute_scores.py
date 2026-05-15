#!/usr/bin/env python3
"""
Calcule les métriques d’erreur entre prévisions et observations, puis alimente forecast_scores.

Métriques :
- Température : MAE / RMSE sur temp_mean
- Vent : MAE sur vitesse
- Pluie : précision binaire (seuil 0.1 mm) et MAE sur quantité ; Brier sur probabilité si présente
"""
from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from datetime import date, timedelta

import numpy as np

from lib.db import connection, query_all, query_one


RAIN_THRESHOLD_MM = 0.1


def _explain_no_pairs(start: date, end: date) -> None:
    """Diagnostic : souvent aucune prévision ancienne dont le jour cible est déjà réalisé."""
    sql_obs = """
    SELECT COUNT(*)::int AS n FROM observations o
    WHERE o.source = 'open_meteo_archive' AND o.obs_date BETWEEN %s AND %s
    """
    sql_fcst_in_window = """
    SELECT COUNT(*)::int AS n FROM forecasts f
    WHERE (f.valid_time AT TIME ZONE 'Europe/Paris')::date BETWEEN %s AND %s
    """
    sql_fcst_past_target = """
    SELECT COUNT(*)::int AS n FROM forecasts f
    WHERE (f.valid_time AT TIME ZONE 'Europe/Paris')::date <= %s
    """
    yesterday = date.today() - timedelta(days=1)
    with connection() as conn:
        o = query_one(conn, sql_obs, (start, end)) or {"n": 0}
        f_win = query_one(conn, sql_fcst_in_window, (start, end)) or {"n": 0}
        f_past = query_one(conn, sql_fcst_past_target, (yesterday,)) or {"n": 0}

    print("Aucune paire prevision/observation dans la fenetre demandee.")
    print(f"  Fenetre scores: {start} -> {end} (jours d'observation passes).")
    print(f"  Observations archive dans la fenetre: {o['n']}")
    print(f"  Previsions dont la date cible (Paris) est dans cette fenetre: {f_win['n']}")
    print(f"  Previsions dont la date cible est deja passee (<= veille): {f_past['n']}")
    print()
    print("Les previsions du premier run visent des jours encore futurs : pour scorer,")
    print("il faut des runs quotidiens (cron) pendant au moins ~une semaine, puis relancer")
    print("compute_scores. Elargir --days aide seulement si l'historique de runs existe deja.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Calcul des scores de prévision")
    p.add_argument("--days", type=int, default=30, help="Fenêtre glissante (jours d’observation)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=args.days - 1)

    sql_pairs = """
    SELECT
      f.provider_id,
      p.code AS provider_code,
      f.city_id,
      c.slug AS city_slug,
      f.lead_days,
      f.temp_mean_c AS f_temp,
      f.wind_speed_ms AS f_wind,
      f.precip_amount_mm AS f_rain,
      f.precip_prob AS f_prob,
      o.temp_mean_c AS o_temp,
      o.wind_speed_max_ms AS o_wind,
      o.precip_sum_mm AS o_rain
    FROM forecasts f
    JOIN observations o
      ON o.city_id = f.city_id
     AND o.source = 'open_meteo_archive'
     AND o.obs_date = (f.valid_time AT TIME ZONE 'Europe/Paris')::date
    JOIN providers p ON p.id = f.provider_id
    JOIN cities c ON c.id = f.city_id
    WHERE o.obs_date BETWEEN %s AND %s
      AND f.temp_mean_c IS NOT NULL
      AND o.temp_mean_c IS NOT NULL
    """

    with connection() as conn:
        rows = query_all(conn, sql_pairs, (start, end))
    if not rows:
        _explain_no_pairs(start, end)
        return

    pair_counts = Counter(r["provider_code"] for r in rows)
    print("Paires prevision/observation (lignes jointes) par fournisseur :")
    for code, n in sorted(pair_counts.items()):
        print(f"  {code}: {n}")
    print(
        "(Si un fournisseur vient seulement de collect_forecasts 'live', ses dates cibles sont "
        "souvent encore dans le futur : 0 paire tant qu'il n'y a pas d'historique de runs "
        "ou de backfill passe - seul open_meteo a un backfill historique pour l'instant.)"
    )

    # Regroupement par (provider_id, city_id, lead_days)
    groups: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["provider_id"], r["city_id"], r["lead_days"])
        groups[key].append(r)

    with connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM forecast_scores
            WHERE score_window_start = %s AND score_window_end = %s
            """,
            (start, end),
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

            # Vent : ignorer les NaN
            fw = [x["f_wind"] for x in items]
            ow = [x["o_wind"] for x in items]
            wind_pairs = [(float(a), float(b)) for a, b in zip(fw, ow) if a is not None and b is not None]
            mae_w = float(np.mean(np.abs(np.array([a - b for a, b in wind_pairs])))) if wind_pairs else None

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
                    p = p_raw / 100.0 if p_raw > 1.0 else p_raw
                    p = min(max(p, 0.0), 1.0)
                    brier_sum += (p - o_bin) ** 2
                brier = brier_sum / len(brier_pairs)

            cur.execute(
                insert_sql,
                (
                    pid,
                    cid,
                    lead,
                    start,
                    end,
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
            f"Scores inseres pour {len(groups)} groupes "
            f"(ville x horizon x fournisseur). Fenetre {start} -> {end}."
        )


if __name__ == "__main__":
    main()
