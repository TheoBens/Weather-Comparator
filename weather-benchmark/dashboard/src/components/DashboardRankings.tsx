"use client";

import { useMemo, useState } from "react";

import { CityRankMatrix } from "@/components/CityRankMatrix";
import { CriterionSelect } from "@/components/CriterionSelect";
import { HorizonMatrix } from "@/components/HorizonMatrix";
import {
  BRIER_COLUMN_TITLE,
  DEFAULT_RANK_CRITERION,
  TABLE_METRIC_COLUMNS,
  formatGlobalCell,
  getCriterion,
  sortProvidersByCriterion,
  type RankCriterionId,
} from "@/lib/ranking-criteria";
import type { CityProviderMetricRow, HorizonProviderRow, ProviderGlobalRow } from "@/lib/scores";
import { FAIR_LEADERBOARD_MAX_HORIZON } from "@/lib/scores";

type Props = {
  globalRows: ProviderGlobalRow[];
  cityMetricRows: CityProviderMetricRow[];
  horizonRows: HorizonProviderRow[];
};

export function DashboardRankings({ globalRows, cityMetricRows, horizonRows }: Props) {
  const [globalCriterionId, setGlobalCriterionId] =
    useState<RankCriterionId>(DEFAULT_RANK_CRITERION);

  const sortedGlobal = useMemo(
    () => sortProvidersByCriterion(globalRows, globalCriterionId),
    [globalRows, globalCriterionId],
  );

  return (
    <>
      <section className="space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Classement global</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Horizons J+1 à J+{FAIR_LEADERBOARD_MAX_HORIZON} (même couverture pour toutes les
              météos)
            </p>
          </div>
          <CriterionSelect
            id="global-criterion"
            value={globalCriterionId}
            onChange={setGlobalCriterionId}
          />
        </div>

        <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/50 shadow-xl shadow-sky-950/50">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-slate-400">
                <th className="px-4 py-3 font-medium">Rang</th>
                <th className="px-4 py-3 font-medium">Fournisseur</th>
                {TABLE_METRIC_COLUMNS.map((id) => {
                  const col = getCriterion(id);
                  const active = id === globalCriterionId;
                  return (
                    <th
                      key={id}
                      title={id === "brier" ? BRIER_COLUMN_TITLE : undefined}
                      className={`px-4 py-3 font-medium ${active ? "text-sky-200" : ""}`}
                    >
                      {col.columnLabel}
                      {active ? " ★" : ""}
                    </th>
                  );
                })}
                <th className="px-4 py-3 font-medium">Échantillons</th>
              </tr>
            </thead>
            <tbody>
              {sortedGlobal.map((r, i) => (
                <tr
                  key={r.code}
                  className="border-b border-white/5 hover:bg-white/[0.04]"
                >
                  <td className="px-4 py-3 font-mono text-sky-300">{i + 1}</td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-white">{r.name}</span>
                    <span className="ml-2 font-mono text-xs text-slate-500">{r.code}</span>
                  </td>
                  {TABLE_METRIC_COLUMNS.map((id) => {
                    const active = id === globalCriterionId;
                    return (
                      <td
                        key={id}
                        className={`px-4 py-3 font-mono ${
                          active
                            ? "font-medium text-emerald-200/95"
                            : "text-slate-300"
                        }`}
                      >
                        {formatGlobalCell(r, id)}
                      </td>
                    );
                  })}
                  <td className="px-4 py-3 font-mono text-slate-500">{r.totalSamples}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <HorizonMatrix rows={horizonRows} />

      <CityRankMatrix rows={cityMetricRows} />
    </>
  );
}
