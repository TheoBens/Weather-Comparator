"use client";

import { useMemo, useState } from "react";

import { CriterionSelect } from "@/components/CriterionSelect";
import {
  DEFAULT_RANK_CRITERION,
  formatMetricValue,
  getCriterion,
  metricFromHorizon,
  type RankCriterionId,
} from "@/lib/ranking-criteria";
import type { HorizonProviderRow } from "@/lib/scores";

const HORIZONS = [1, 2, 3, 4, 5, 6, 7] as const;

type Props = {
  rows: HorizonProviderRow[];
};

export function HorizonMatrix({ rows }: Props) {
  const [criterionId, setCriterionId] = useState<RankCriterionId>(DEFAULT_RANK_CRITERION);
  const criterion = getCriterion(criterionId);

  const sortedRows = useMemo(
    () => [...rows].sort((a, b) => a.code.localeCompare(b.code)),
    [rows],
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="text-xl font-semibold text-white">Par horizon</h2>
        <CriterionSelect
          id="horizon-criterion"
          value={criterionId}
          onChange={setCriterionId}
          label="Métrique"
        />
      </div>
      <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/50">
        <table className="w-full min-w-[880px] text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-slate-400">
              <th className="px-3 py-3 font-medium">Fournisseur</th>
              {HORIZONS.map((h) => (
                <th key={h} className="px-2 py-3 text-center font-medium">
                  J+{h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr key={row.code} className="border-b border-white/5 hover:bg-white/[0.04]">
                <td className="px-3 py-2.5">
                  <span className="text-white">{row.name}</span>
                  <span className="ml-1 font-mono text-xs text-slate-500">{row.code}</span>
                </td>
                {HORIZONS.map((h) => {
                  const values = row.byHorizon[h];
                  const raw = values ? metricFromHorizon(values, criterionId) : null;
                  return (
                    <td
                      key={h}
                      className="px-2 py-2.5 text-center font-mono text-slate-200"
                    >
                      {formatMetricValue(raw, criterion.format)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
