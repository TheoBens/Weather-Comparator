import type postgres from "postgres";

/** Classements global et par ville : horizons J+1…J+3 (couverture ~ Météo-France). */
export const FAIR_LEADERBOARD_MAX_HORIZON = 3;

export type ScoreWindow = {
  start: string;
  end: string;
};

export type ProviderGlobalRow = {
  code: string;
  name: string;
  avgMaeTemp: number | null;
  avgRmseTemp: number | null;
  avgMaeWind: number | null;
  avgRainAcc: number | null;
  avgRainMae: number | null;
  avgBrier: number | null;
  totalSamples: number;
};

export type HorizonMetricValues = {
  avgMaeTemp: number | null;
  avgRmseTemp: number | null;
  avgMaeWind: number | null;
  avgRainAcc: number | null;
  avgRainMae: number | null;
  avgBrier: number | null;
};

export type HorizonProviderRow = {
  code: string;
  name: string;
  byHorizon: Record<number, HorizonMetricValues>;
};

export type CityBestRow = {
  citySlug: string;
  cityName: string;
  bestProviderCode: string;
  bestProviderName: string;
  avgMaeTemp: number | null;
};

/** Métriques agrégées par ville × fournisseur (pour classement dynamique côté client). */
export type CityProviderMetricRow = {
  citySlug: string;
  cityName: string;
  providerCode: string;
  providerName: string;
  avgMaeTemp: number | null;
  avgRmseTemp: number | null;
  avgMaeWind: number | null;
  avgRainAcc: number | null;
  avgRainMae: number | null;
  avgBrier: number | null;
};

/** Meilleur fournisseur par ville selon précision sec/pluie (moyenne sur horizons). */
export type CityBestByRainRow = {
  citySlug: string;
  cityName: string;
  bestProviderCode: string;
  bestProviderName: string;
  avgRainAcc: number | null;
};

function toDateString(v: unknown): string | null {
  if (v == null) return null;
  if (typeof v === "string") return v.slice(0, 10);
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  return String(v).slice(0, 10);
}

export async function fetchLatestScoreWindow(
  sql: postgres.Sql,
): Promise<ScoreWindow | null> {
  const rows = await sql<{ wstart: Date | string; wend: Date | string }[]>`
    SELECT DISTINCT score_window_start AS wstart, score_window_end AS wend FROM forecast_scores
  `;
  if (!rows.length) return null;
  const sorted = rows
    .map((r) => ({
      start: toDateString(r.wstart)!,
      end: toDateString(r.wend)!,
    }))
    .sort((a, b) => {
      const endCmp =
        Number(b.end.replaceAll("-", "")) - Number(a.end.replaceAll("-", ""));
      if (endCmp !== 0) return endCmp;
      return Number(b.start.replaceAll("-", "")) - Number(a.start.replaceAll("-", ""));
    });
  return sorted[0]!;
}

export async function fetchGlobalLeaderboard(
  sql: postgres.Sql,
  windowStart: string,
  windowEnd: string,
): Promise<ProviderGlobalRow[]> {
  const rows = await sql<
    {
      code: string;
      name: string;
      avg_mae_temp: string | null;
      avg_rmse_temp: string | null;
      avg_mae_wind: string | null;
      avg_rain_acc: string | null;
      avg_rain_mae: string | null;
      avg_brier: string | null;
      total_samples: string | null;
    }[]
  >`
    SELECT
      p.code,
      p.name,
      AVG(fs.mae_temp_c)::float8 AS avg_mae_temp,
      AVG(fs.rmse_temp_c)::float8 AS avg_rmse_temp,
      AVG(fs.mae_wind_ms)::float8 AS avg_mae_wind,
      AVG(fs.rain_binary_accuracy)::float8 AS avg_rain_acc,
      AVG(fs.rain_mae_mm)::float8 AS avg_rain_mae,
      AVG(fs.precip_prob_brier)::float8 AS avg_brier,
      SUM(fs.n_samples)::bigint AS total_samples
    FROM forecast_scores fs
    JOIN providers p ON p.id = fs.provider_id
    WHERE fs.score_window_start = ${windowStart}::date
      AND fs.score_window_end = ${windowEnd}::date
      AND fs.horizon_days <= ${FAIR_LEADERBOARD_MAX_HORIZON}
    GROUP BY p.id, p.code, p.name
    ORDER BY avg_mae_temp ASC NULLS LAST
  `;
  return rows.map((r) => ({
    code: r.code,
    name: r.name,
    avgMaeTemp: r.avg_mae_temp != null ? Number(r.avg_mae_temp) : null,
    avgRmseTemp: r.avg_rmse_temp != null ? Number(r.avg_rmse_temp) : null,
    avgMaeWind: r.avg_mae_wind != null ? Number(r.avg_mae_wind) : null,
    avgRainAcc: r.avg_rain_acc != null ? Number(r.avg_rain_acc) : null,
    avgRainMae: r.avg_rain_mae != null ? Number(r.avg_rain_mae) : null,
    avgBrier: r.avg_brier != null ? Number(r.avg_brier) : null,
    totalSamples: Number(r.total_samples ?? 0),
  }));
}

export async function fetchHorizonMatrix(
  sql: postgres.Sql,
  windowStart: string,
  windowEnd: string,
): Promise<HorizonProviderRow[]> {
  const rows = await sql<
    {
      code: string;
      name: string;
      horizon_days: number;
      avg_mae_temp: string | null;
      avg_rmse_temp: string | null;
      avg_mae_wind: string | null;
      avg_rain_acc: string | null;
      avg_rain_mae: string | null;
      avg_brier: string | null;
    }[]
  >`
    SELECT
      p.code,
      p.name,
      fs.horizon_days,
      AVG(fs.mae_temp_c)::float8 AS avg_mae_temp,
      AVG(fs.rmse_temp_c)::float8 AS avg_rmse_temp,
      AVG(fs.mae_wind_ms)::float8 AS avg_mae_wind,
      AVG(fs.rain_binary_accuracy)::float8 AS avg_rain_acc,
      AVG(fs.rain_mae_mm)::float8 AS avg_rain_mae,
      AVG(fs.precip_prob_brier)::float8 AS avg_brier
    FROM forecast_scores fs
    JOIN providers p ON p.id = fs.provider_id
    WHERE fs.score_window_start = ${windowStart}::date
      AND fs.score_window_end = ${windowEnd}::date
    GROUP BY p.id, p.code, p.name, fs.horizon_days
    ORDER BY p.code, fs.horizon_days
  `;
  const byCode = new Map<string, HorizonProviderRow>();
  for (const r of rows) {
    let cell = byCode.get(r.code);
    if (!cell) {
      cell = { code: r.code, name: r.name, byHorizon: {} };
      byCode.set(r.code, cell);
    }
    cell.byHorizon[r.horizon_days] = {
      avgMaeTemp: r.avg_mae_temp != null ? Number(r.avg_mae_temp) : null,
      avgRmseTemp: r.avg_rmse_temp != null ? Number(r.avg_rmse_temp) : null,
      avgMaeWind: r.avg_mae_wind != null ? Number(r.avg_mae_wind) : null,
      avgRainAcc: r.avg_rain_acc != null ? Number(r.avg_rain_acc) : null,
      avgRainMae: r.avg_rain_mae != null ? Number(r.avg_rain_mae) : null,
      avgBrier: r.avg_brier != null ? Number(r.avg_brier) : null,
    };
  }
  return Array.from(byCode.values()).sort((a, b) => a.code.localeCompare(b.code));
}

export async function fetchCityBestProvider(
  sql: postgres.Sql,
  windowStart: string,
  windowEnd: string,
): Promise<CityBestRow[]> {
  const rows = await sql`
    WITH ranked AS (
      SELECT
        c.slug,
        c.name AS city_name,
        p.code,
        p.name AS provider_name,
        AVG(fs.mae_temp_c)::float8 AS avg_mae,
        ROW_NUMBER() OVER (
          PARTITION BY c.id
          ORDER BY AVG(fs.mae_temp_c) ASC NULLS LAST
        ) AS rn
      FROM forecast_scores fs
      JOIN cities c ON c.id = fs.city_id
      JOIN providers p ON p.id = fs.provider_id
      WHERE fs.score_window_start = ${windowStart}::date
        AND fs.score_window_end = ${windowEnd}::date
      GROUP BY c.id, c.slug, c.name, p.id, p.code, p.name
    )
    SELECT slug, city_name, code, provider_name, avg_mae
    FROM ranked
    WHERE rn = 1
    ORDER BY city_name
  `;
  return rows.map((r) => ({
    citySlug: r.slug as string,
    cityName: r.city_name as string,
    bestProviderCode: r.code as string,
    bestProviderName: r.provider_name as string,
    avgMaeTemp: r.avg_mae != null ? Number(r.avg_mae) : null,
  }));
}

export async function fetchCityBestProviderByRain(
  sql: postgres.Sql,
  windowStart: string,
  windowEnd: string,
): Promise<CityBestByRainRow[]> {
  const rows = await sql`
    WITH ranked AS (
      SELECT
        c.slug,
        c.name AS city_name,
        p.code,
        p.name AS provider_name,
        AVG(fs.rain_binary_accuracy)::float8 AS avg_rain,
        ROW_NUMBER() OVER (
          PARTITION BY c.id
          ORDER BY AVG(fs.rain_binary_accuracy) DESC NULLS LAST
        ) AS rn
      FROM forecast_scores fs
      JOIN cities c ON c.id = fs.city_id
      JOIN providers p ON p.id = fs.provider_id
      WHERE fs.score_window_start = ${windowStart}::date
        AND fs.score_window_end = ${windowEnd}::date
      GROUP BY c.id, c.slug, c.name, p.id, p.code, p.name
    )
    SELECT slug, city_name, code, provider_name, avg_rain
    FROM ranked
    WHERE rn = 1
    ORDER BY city_name
  `;
  return rows.map((r) => ({
    citySlug: r.slug as string,
    cityName: r.city_name as string,
    bestProviderCode: r.code as string,
    bestProviderName: r.provider_name as string,
    avgRainAcc: r.avg_rain != null ? Number(r.avg_rain) : null,
  }));
}

export async function fetchCityProviderMetrics(
  sql: postgres.Sql,
  windowStart: string,
  windowEnd: string,
): Promise<CityProviderMetricRow[]> {
  const rows = await sql<
    {
      slug: string;
      city_name: string;
      code: string;
      provider_name: string;
      avg_mae_temp: string | null;
      avg_rmse_temp: string | null;
      avg_mae_wind: string | null;
      avg_rain_acc: string | null;
      avg_rain_mae: string | null;
      avg_brier: string | null;
    }[]
  >`
    SELECT
      c.slug,
      c.name AS city_name,
      p.code,
      p.name AS provider_name,
      AVG(fs.mae_temp_c)::float8 AS avg_mae_temp,
      AVG(fs.rmse_temp_c)::float8 AS avg_rmse_temp,
      AVG(fs.mae_wind_ms)::float8 AS avg_mae_wind,
      AVG(fs.rain_binary_accuracy)::float8 AS avg_rain_acc,
      AVG(fs.rain_mae_mm)::float8 AS avg_rain_mae,
      AVG(fs.precip_prob_brier)::float8 AS avg_brier
    FROM forecast_scores fs
    JOIN cities c ON c.id = fs.city_id
    JOIN providers p ON p.id = fs.provider_id
    WHERE fs.score_window_start = ${windowStart}::date
      AND fs.score_window_end = ${windowEnd}::date
      AND fs.horizon_days <= ${FAIR_LEADERBOARD_MAX_HORIZON}
    GROUP BY c.id, c.slug, c.name, p.id, p.code, p.name
    ORDER BY c.name, p.code
  `;
  return rows.map((r) => ({
    citySlug: r.slug,
    cityName: r.city_name,
    providerCode: r.code,
    providerName: r.provider_name,
    avgMaeTemp: r.avg_mae_temp != null ? Number(r.avg_mae_temp) : null,
    avgRmseTemp: r.avg_rmse_temp != null ? Number(r.avg_rmse_temp) : null,
    avgMaeWind: r.avg_mae_wind != null ? Number(r.avg_mae_wind) : null,
    avgRainAcc: r.avg_rain_acc != null ? Number(r.avg_rain_acc) : null,
    avgRainMae: r.avg_rain_mae != null ? Number(r.avg_rain_mae) : null,
    avgBrier: r.avg_brier != null ? Number(r.avg_brier) : null,
  }));
}
