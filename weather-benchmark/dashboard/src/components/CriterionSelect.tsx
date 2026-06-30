"use client";

import {
  getCriteriaInTableOrder,
  type RankCriterionId,
} from "@/lib/ranking-criteria";

type Props = {
  id: string;
  value: RankCriterionId;
  onChange: (id: RankCriterionId) => void;
  label?: string;
};

export function CriterionSelect({
  id,
  value,
  onChange,
  label = "Classer par",
}: Props) {
  return (
    <label
      htmlFor={id}
      className="flex min-w-[min(100%,20rem)] flex-col gap-1.5 text-sm text-slate-300"
    >
      <span className="font-medium text-sky-200/90">{label}</span>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as RankCriterionId)}
        className="rounded-lg border border-white/15 bg-slate-900/80 px-3 py-2.5 text-white shadow-inner shadow-black/20 outline-none ring-sky-500/40 focus:ring-2"
      >
        {getCriteriaInTableOrder().map((c) => (
          <option key={c.id} value={c.id}>
            {c.label}
          </option>
        ))}
      </select>
    </label>
  );
}
