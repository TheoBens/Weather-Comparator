import type postgres from "postgres";

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

export type HorizonCell = {
  code: string;
  name: string;
  byHorizon: Record<number, number | null>;
};

export type CityBestRow = {
  citySlug: string;
  cityName: string;
  bestProviderCode: string;
  bestProviderName: string;
  avgMaeTemp: number | null;
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
  const [row] = await sql<{ mx: Date | string | null }[]>`
    SELECT MAX(score_window_end) AS mx FROM forecast_scores
  `;
  const end = toDateString(row?.mx ?? null);
  if (!end) return null;
  const [bounds] = await sql<{ mn: Date | string | null }[]>`
    SELECT MIN(score_window_start) AS mn FROM forecast_scores
    WHERE score_window_end = ${end}::date
  `;
  const start = toDateString(bounds?.mn ?? null) ?? end;
  return { start, end };
}

export async function fetchGlobalLeaderboard(
  sql: postgres.Sql,
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
    WHERE fs.score_window_end = ${windowEnd}::date
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
  windowEnd: string,
): Promise<HorizonCell[]> {
  const rows = await sql<
    {
      code: string;
      name: string;
      horizon_days: number;
      mae: string | null;
    }[]
  >`
    SELECT
      p.code,
      p.name,
      fs.horizon_days,
      AVG(fs.mae_temp_c)::float8 AS mae
    FROM forecast_scores fs
    JOIN providers p ON p.id = fs.provider_id
    WHERE fs.score_window_end = ${windowEnd}::date
    GROUP BY p.id, p.code, p.name, fs.horizon_days
    ORDER BY p.code, fs.horizon_days
  `;
  const byCode = new Map<string, HorizonCell>();
  for (const r of rows) {
    let cell = byCode.get(r.code);
    if (!cell) {
      cell = { code: r.code, name: r.name, byHorizon: {} };
      byCode.set(r.code, cell);
    }
    cell.byHorizon[r.horizon_days] = r.mae != null ? Number(r.mae) : null;
  }
  return Array.from(byCode.values()).sort((a, b) => a.code.localeCompare(b.code));
}

export async function fetchCityBestProvider(
  sql: postgres.Sql,
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
      WHERE fs.score_window_end = ${windowEnd}::date
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
