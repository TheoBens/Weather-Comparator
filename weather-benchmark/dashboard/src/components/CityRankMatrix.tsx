"use client";

import { useMemo, useState } from "react";

import { CriterionSelect } from "@/components/CriterionSelect";
import {
  DEFAULT_RANK_CRITERION,
  buildCityProviderRankMatrix,
  formatMetricValue,
  getCriterion,
  type RankCriterionId,
} from "@/lib/ranking-criteria";
import type { CityProviderMetricRow } from "@/lib/scores";
import { FAIR_LEADERBOARD_MAX_HORIZON } from "@/lib/scores";

type Props = {
  rows: CityProviderMetricRow[];
};

export function CityRankMatrix({ rows }: Props) {
  const [criterionId, setCriterionId] = useState<RankCriterionId>(DEFAULT_RANK_CRITERION);
  const criterion = getCriterion(criterionId);

  const matrix = useMemo(
    () => buildCityProviderRankMatrix(rows, criterionId),
    [rows, criterionId],
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Classement par ville</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Valeur de la métrique et rang (1 = meilleur) · horizons J+1 à J+
            {FAIR_LEADERBOARD_MAX_HORIZON}
          </p>
        </div>
        <CriterionSelect
          id="city-criterion"
          value={criterionId}
          onChange={setCriterionId}
        />
      </div>

      <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/50">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-slate-400">
              <th className="sticky left-0 z-10 bg-slate-900/95 px-3 py-3 font-medium">
                Ville
              </th>
              {matrix.providers.map((p) => (
                <th
                  key={p.code}
                  className="px-2 py-3 text-center font-medium whitespace-nowrap"
                >
                  <span className="block text-white">{p.name}</span>
                  <span className="font-mono text-xs font-normal text-slate-500">{p.code}</span>
                </th>
              ))}
              <th className="border-l border-white/10 px-3 py-3 text-center font-medium whitespace-nowrap">
                <span className="block text-sky-200">Moy. météos</span>
                <span className="text-xs font-normal text-slate-500">tous fournisseurs</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {matrix.cities.map((city) => (
              <tr key={city.slug} className="border-b border-white/5 hover:bg-white/[0.04]">
                <td className="sticky left-0 z-10 bg-slate-900/95 px-3 py-2.5 font-medium text-white whitespace-nowrap">
                  {city.name}
                </td>
                {matrix.providers.map((p) => {
                  const cell = matrix.cells.get(city.slug)?.get(p.code);
                  const rank = cell?.rank ?? null;
                  const value = cell?.value ?? null;
                  const formatted =
                    value != null
                      ? formatMetricValue(value, criterion.format) + (criterion.unit ?? "")
                      : null;
                  const isBest = rank === 1;
                  return (
                    <td
                      key={p.code}
                      className={`px-2 py-2.5 text-center ${
                        value == null ? "text-slate-600" : ""
                      }`}
                    >
                      {formatted != null ? (
                        <div className="flex flex-col items-center gap-0.5">
                          <span
                            className={`font-mono text-sm leading-tight ${
                              isBest ? "font-semibold text-emerald-300" : "text-slate-100"
                            }`}
                          >
                            {formatted}
                          </span>
                          <span
                            className={`font-mono text-xs ${
                              isBest ? "text-emerald-400/80" : "text-slate-500"
                            }`}
                          >
                            #{rank}
                          </span>
                        </div>
                      ) : (
                        <span className="font-mono text-slate-600">—</span>
                      )}
                    </td>
                  );
                })}
                {(() => {
                  const avg = matrix.cityAverages.get(city.slug) ?? null;
                  const formatted =
                    avg != null
                      ? formatMetricValue(avg, criterion.format) + (criterion.unit ?? "")
                      : null;
                  const nProviders = matrix.providers.filter(
                    (p) => matrix.cells.get(city.slug)?.get(p.code)?.value != null,
                  ).length;
                  return (
                    <td
                      title={
                        nProviders > 0
                          ? `Moyenne arithmétique sur ${nProviders} fournisseur(s)`
                          : undefined
                      }
                      className="border-l border-white/10 px-3 py-2.5 text-center"
                    >
                      {formatted != null ? (
                        <span className="font-mono text-sm font-medium text-sky-200">
                          {formatted}
                        </span>
                      ) : (
                        <span className="font-mono text-slate-600">—</span>
                      )}
                    </td>
                  );
                })()}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
