import type { CityProviderMetricRow, HorizonMetricValues, ProviderGlobalRow } from "@/lib/scores";

export type RankCriterionId =
  | "mae_temp"
  | "rmse_temp"
  | "mae_wind"
  | "rain_acc"
  | "rain_mae"
  | "brier";

export type RankCriterion = {
  id: RankCriterionId;
  label: string;
  /** true = plus la valeur est grande, mieux c'est (ex. précision pluie). */
  higherIsBetter: boolean;
  columnLabel: string;
  format: "decimal" | "percent" | "decimal3";
  unit?: string;
};

const CRITERIA_BY_ID: Record<RankCriterionId, RankCriterion> = {
  rain_acc: {
    id: "rain_acc",
    label: "Précision pluie (sec / mouillé)",
    higherIsBetter: true,
    columnLabel: "Préc. pluie",
    format: "percent",
  },
  rain_mae: {
    id: "rain_mae",
    label: "Pluie (MAE mm)",
    higherIsBetter: false,
    columnLabel: "MAE pluie (mm)",
    format: "decimal",
    unit: " mm",
  },
  brier: {
    id: "brier",
    label: "Probabilité de pluie (Brier)",
    higherIsBetter: false,
    columnLabel: "Brier prob.",
    format: "decimal3",
  },
  mae_temp: {
    id: "mae_temp",
    label: "Température (MAE °C)",
    higherIsBetter: false,
    columnLabel: "MAE T (°C)",
    format: "decimal",
    unit: " °C",
  },
  rmse_temp: {
    id: "rmse_temp",
    label: "Température (RMSE °C)",
    higherIsBetter: false,
    columnLabel: "RMSE T (°C)",
    format: "decimal",
    unit: " °C",
  },
  mae_wind: {
    id: "mae_wind",
    label: "Vent (MAE m/s)",
    higherIsBetter: false,
    columnLabel: "MAE vent (m/s)",
    format: "decimal",
    unit: " m/s",
  },
};

/** Ordre des colonnes métriques dans le tableau global (pluie → température → vent). */
export const TABLE_METRIC_COLUMNS: RankCriterionId[] = [
  "rain_acc",
  "rain_mae",
  "brier",
  "mae_temp",
  "rmse_temp",
  "mae_wind",
];

export const BRIER_COLUMN_TITLE =
  "Score de Brier : qualité des probabilités de pluie. Compare la probabilité annoncée (0–100 %) " +
  "au fait qu’il ait réellement plu (> 0,1 mm). 0 = parfait ; plus la valeur est basse, mieux c’est. " +
  "« — » si l’API ne fournit pas de probabilité.";

export const DEFAULT_RANK_CRITERION: RankCriterionId = "rain_acc";

export function getCriterion(id: RankCriterionId): RankCriterion {
  return CRITERIA_BY_ID[id];
}

/** Options du menu déroulant, dans le même ordre que les colonnes du tableau. */
export function getCriteriaInTableOrder(): RankCriterion[] {
  return TABLE_METRIC_COLUMNS.map((id) => getCriterion(id));
}

function metricFromGlobal(row: ProviderGlobalRow, id: RankCriterionId): number | null {
  switch (id) {
    case "mae_temp":
      return row.avgMaeTemp;
    case "rmse_temp":
      return row.avgRmseTemp;
    case "mae_wind":
      return row.avgMaeWind;
    case "rain_acc":
      return row.avgRainAcc;
    case "rain_mae":
      return row.avgRainMae;
    case "brier":
      return row.avgBrier;
  }
}

function metricFromCity(row: CityProviderMetricRow, id: RankCriterionId): number | null {
  switch (id) {
    case "mae_temp":
      return row.avgMaeTemp;
    case "rmse_temp":
      return row.avgRmseTemp;
    case "mae_wind":
      return row.avgMaeWind;
    case "rain_acc":
      return row.avgRainAcc;
    case "rain_mae":
      return row.avgRainMae;
    case "brier":
      return row.avgBrier;
  }
}

export function metricFromHorizon(
  row: HorizonMetricValues,
  id: RankCriterionId,
): number | null {
  switch (id) {
    case "mae_temp":
      return row.avgMaeTemp;
    case "rmse_temp":
      return row.avgRmseTemp;
    case "mae_wind":
      return row.avgMaeWind;
    case "rain_acc":
      return row.avgRainAcc;
    case "rain_mae":
      return row.avgRainMae;
    case "brier":
      return row.avgBrier;
  }
}

export function sortProvidersByCriterion(
  rows: ProviderGlobalRow[],
  criterionId: RankCriterionId,
): ProviderGlobalRow[] {
  const { higherIsBetter } = getCriterion(criterionId);
  return [...rows].sort((a, b) => {
    const av = metricFromGlobal(a, criterionId);
    const bv = metricFromGlobal(b, criterionId);
    if (av == null && bv == null) return a.code.localeCompare(b.code);
    if (av == null) return 1;
    if (bv == null) return -1;
    const d = higherIsBetter ? bv - av : av - bv;
    return d !== 0 ? d : a.code.localeCompare(b.code);
  });
}

export type CityRankCell = {
  rank: number | null;
  value: number | null;
};

export type CityProviderRankMatrix = {
  cities: { slug: string; name: string }[];
  providers: { code: string; name: string }[];
  /** citySlug → providerCode */
  cells: Map<string, Map<string, CityRankCell>>;
  /** Moyenne de la métrique sur les fournisseurs ayant une valeur, par ville. */
  cityAverages: Map<string, number | null>;
};

export function buildCityProviderRankMatrix(
  rows: CityProviderMetricRow[],
  criterionId: RankCriterionId,
): CityProviderRankMatrix {
  const { higherIsBetter } = getCriterion(criterionId);
  const byCity = new Map<string, CityProviderMetricRow[]>();
  const providerMap = new Map<string, string>();

  for (const r of rows) {
    providerMap.set(r.providerCode, r.providerName);
    const list = byCity.get(r.citySlug) ?? [];
    list.push(r);
    byCity.set(r.citySlug, list);
  }

  const cities = [...byCity.values()]
    .map((group) => ({ slug: group[0]!.citySlug, name: group[0]!.cityName }))
    .sort((a, b) => a.name.localeCompare(b.name, "fr"));

  const providers = [...providerMap.entries()]
    .map(([code, name]) => ({ code, name }))
    .sort((a, b) => a.code.localeCompare(b.code));

  const cells = new Map<string, Map<string, CityRankCell>>();
  const cityAverages = new Map<string, number | null>();

  for (const { slug } of cities) {
    const group = byCity.get(slug) ?? [];
    const sorted = [...group].sort((a, b) => {
      const av = metricFromCity(a, criterionId);
      const bv = metricFromCity(b, criterionId);
      if (av == null && bv == null) return a.providerCode.localeCompare(b.providerCode);
      if (av == null) return 1;
      if (bv == null) return -1;
      const d = higherIsBetter ? bv - av : av - bv;
      return d !== 0 ? d : a.providerCode.localeCompare(b.providerCode);
    });

    const cityCells = new Map<string, CityRankCell>();
    let rank = 0;
    for (const row of sorted) {
      const value = metricFromCity(row, criterionId);
      if (value != null) rank += 1;
      cityCells.set(row.providerCode, {
        rank: value != null ? rank : null,
        value,
      });
    }
    cells.set(slug, cityCells);

    const metricValues = group
      .map((row) => metricFromCity(row, criterionId))
      .filter((v): v is number => v != null && !Number.isNaN(v));
    cityAverages.set(
      slug,
      metricValues.length > 0
        ? metricValues.reduce((sum, v) => sum + v, 0) / metricValues.length
        : null,
    );
  }

  return { cities, providers, cells, cityAverages };
}

export type CityBestDisplay = {
  citySlug: string;
  cityName: string;
  bestProviderCode: string;
  bestProviderName: string;
  metricValue: number | null;
};

export function bestProviderPerCity(
  rows: CityProviderMetricRow[],
  criterionId: RankCriterionId,
): CityBestDisplay[] {
  const { higherIsBetter } = getCriterion(criterionId);
  const byCity = new Map<string, CityProviderMetricRow[]>();
  for (const r of rows) {
    const list = byCity.get(r.citySlug) ?? [];
    list.push(r);
    byCity.set(r.citySlug, list);
  }

  const out: CityBestDisplay[] = [];
  for (const group of byCity.values()) {
    const sorted = [...group].sort((a, b) => {
      const av = metricFromCity(a, criterionId);
      const bv = metricFromCity(b, criterionId);
      if (av == null && bv == null) return a.providerCode.localeCompare(b.providerCode);
      if (av == null) return 1;
      if (bv == null) return -1;
      const d = higherIsBetter ? bv - av : av - bv;
      return d !== 0 ? d : a.providerCode.localeCompare(b.providerCode);
    });
    const best = sorted[0]!;
    out.push({
      citySlug: best.citySlug,
      cityName: best.cityName,
      bestProviderCode: best.providerCode,
      bestProviderName: best.providerName,
      metricValue: metricFromCity(best, criterionId),
    });
  }
  return out.sort((a, b) => a.cityName.localeCompare(b.cityName, "fr"));
}

export function formatMetricValue(
  value: number | null | undefined,
  format: RankCriterion["format"],
): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (format === "percent") {
    return (
      (value * 100).toLocaleString("fr-FR", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }) + " %"
    );
  }
  const digits = format === "decimal3" ? 3 : 2;
  return value.toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatGlobalCell(
  row: ProviderGlobalRow,
  id: RankCriterionId,
): string {
  const c = getCriterion(id);
  return formatMetricValue(metricFromGlobal(row, id), c.format);
}
