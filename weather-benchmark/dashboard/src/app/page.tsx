import { getDb } from "@/lib/db";
import type { ProviderGlobalRow } from "@/lib/scores";
import {
  fetchCityBestProvider,
  fetchCityBestProviderByRain,
  fetchGlobalLeaderboard,
  fetchHorizonMatrix,
  fetchLatestScoreWindow,
} from "@/lib/scores";

export const dynamic = "force-dynamic";

function fmt(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtPct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return (n * 100).toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }) + " %";
}

/** Pour le classement « pluie » : meilleure précision d’abord ; sans donnée en dernier. */
function sortGlobalByRainAccDesc(rows: ProviderGlobalRow[]): ProviderGlobalRow[] {
  return [...rows].sort((a, b) => {
    const av = a.avgRainAcc;
    const bv = b.avgRainAcc;
    if (av == null && bv == null) return a.code.localeCompare(b.code);
    if (av == null) return 1;
    if (bv == null) return -1;
    const d = bv - av;
    return d !== 0 ? d : a.code.localeCompare(b.code);
  });
}

export default async function Home() {
  let sql: ReturnType<typeof getDb> = null;
  let dbConfigError: string | null = null;
  try {
    sql = getDb();
  } catch (e) {
    dbConfigError = e instanceof Error ? e.message : String(e);
  }

  if (dbConfigError) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-sky-950 to-slate-950 px-6 py-16 text-slate-100">
        <main className="mx-auto max-w-3xl space-y-6">
          <h1 className="text-3xl font-semibold text-white">Météos comparateur</h1>
          <div className="rounded-2xl border border-amber-500/40 bg-amber-950/40 p-6">
            <p className="font-medium text-amber-100">Configuration Postgres (.env.local)</p>
            <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-black/40 p-4 font-mono text-sm text-amber-50/95">
              {dbConfigError}
            </pre>
            <p className="mt-4 text-sm text-amber-200/85">
              Copie depuis Supabase → Database → <strong>Session pooler</strong> les valeurs{" "}
              <code className="rounded bg-black/30 px-1">Host</code>,{" "}
              <code className="rounded bg-black/30 px-1">User</code> (souvent{" "}
              <code className="rounded bg-black/30 px-1">postgres.xxxxx</code>),{" "}
              <code className="rounded bg-black/30 px-1">Password</code>. Redémarre{" "}
              <code className="rounded bg-black/30 px-1">npm run dev</code> après modification.
            </p>
          </div>
        </main>
      </div>
    );
  }

  if (!sql) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-sky-950 to-slate-950 px-6 py-16 text-slate-100">
        <main className="mx-auto max-w-3xl space-y-6">
          <h1 className="text-3xl font-semibold text-white">Météos comparateur</h1>
          <div className="rounded-2xl border border-amber-500/40 bg-amber-950/40 p-6">
            <p className="font-medium text-amber-100">Connexion base de données</p>
            <p className="mt-2 text-sm text-amber-200/90">
              Crée <code className="rounded bg-black/30 px-1.5 py-0.5">dashboard/.env.local</code>{" "}
              avec les <strong>mêmes</strong> variables que{" "}
              <code className="rounded bg-black/30 px-1">scripts/.env</code> : soit{" "}
              <code className="rounded bg-black/30 px-1">POSTGRES_*</code> (pooler), soit une
              vraie <code className="rounded bg-black/30 px-1">DATABASE_URL</code> (pas le
              placeholder <code className="rounded bg-black/30 px-1">PROJECT_REF</code>).
            </p>
            <p className="mt-2 text-sm text-amber-200/70">
              Erreur Supabase « Tenant or user not found » : souvent{" "}
              <code className="rounded bg-black/30 px-1">POSTGRES_USER</code> doit être{" "}
              <code className="rounded bg-black/30 px-1">postgres.ton_ref</code>, pas seulement{" "}
              <code className="rounded bg-black/30 px-1">postgres</code>, avec l&apos;hôte{" "}
              <code className="rounded bg-black/30 px-1">*.pooler.supabase.com</code>.
            </p>
            <p className="mt-3 text-sm text-amber-200/80">
              Sous Vercel : copie les mêmes variables (ou <code className="rounded bg-black/30 px-1">DATABASE_URL</code>).
            </p>
          </div>
        </main>
      </div>
    );
  }

  let errorMessage: string | null = null;
  let windowBounds: Awaited<ReturnType<typeof fetchLatestScoreWindow>> = null;
  let globalRows: Awaited<ReturnType<typeof fetchGlobalLeaderboard>> = [];
  let horizonRows: Awaited<ReturnType<typeof fetchHorizonMatrix>> = [];
  let cityRows: Awaited<ReturnType<typeof fetchCityBestProvider>> = [];
  let cityRainRows: Awaited<ReturnType<typeof fetchCityBestProviderByRain>> = [];

  try {
    windowBounds = await fetchLatestScoreWindow(sql);
    if (windowBounds) {
      const { start: wStart, end: wEnd } = windowBounds;
      [globalRows, horizonRows, cityRows, cityRainRows] = await Promise.all([
        fetchGlobalLeaderboard(sql, wStart, wEnd),
        fetchHorizonMatrix(sql, wStart, wEnd),
        fetchCityBestProvider(sql, wStart, wEnd),
        fetchCityBestProviderByRain(sql, wStart, wEnd),
      ]);
    }
  } catch (e) {
    errorMessage = e instanceof Error ? e.message : String(e);
  }

  const horizons = [1, 2, 3, 4, 5, 6, 7] as const;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-sky-950/90 to-slate-950 text-slate-100">
      <main className="mx-auto max-w-6xl space-y-10 px-4 py-12 sm:px-6">
        <header className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">
            Bench comparatif
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Météos comparateur
          </h1>
          <p className="max-w-2xl text-slate-300">
            Classements à partir des scores en base (température, vent, pluie). Les
            autres fournisseurs météo seront branchés ensuite.
          </p>
          {windowBounds && (
            <p className="text-sm text-sky-200/90">
              Fenêtre d&apos;évaluation :{" "}
              <span className="font-mono text-white">
                {windowBounds.start} → {windowBounds.end}
              </span>
            </p>
          )}
        </header>

        {errorMessage && (
          <div className="rounded-2xl border border-red-500/50 bg-red-950/50 p-5 text-red-100">
            <p className="font-medium">Erreur requête SQL</p>
            <pre className="mt-2 whitespace-pre-wrap font-mono text-xs opacity-90">
              {errorMessage}
            </pre>
            {(errorMessage.includes("ECIRCUITBREAKER") ||
              errorMessage.toLowerCase().includes("circuit breaker") ||
              errorMessage.toLowerCase().includes("temporarily blocked")) && (
              <div className="mt-4 rounded-lg border border-orange-400/40 bg-orange-950/40 p-4 text-sm leading-relaxed text-orange-50">
                <p className="font-medium text-white">Blocage temporaire Supabase</p>
                <p className="mt-2 text-orange-100/95">
                  Trop de tentatives de connexion avec un identifiant / mot de passe incorrect :
                  Supabase coupe brièvement les nouvelles connexions (circuit breaker).
                </p>
                <ul className="mt-2 list-inside list-disc space-y-1 text-orange-100/90">
                  <li>
                    Attends en général <strong>15 à 60 minutes</strong> sans recharger la page ni
                    lancer <code className="rounded bg-black/30 px-1">npm run dev</code> en boucle.
                  </li>
                  <li>
                    Pendant ce temps, corrige <code className="rounded bg-black/30 px-1">.env.local</code>{" "}
                    (copie exacte du bloc qui marche dans{" "}
                    <code className="rounded bg-black/30 px-1">scripts/.env</code>).
                  </li>
                  <li>
                    Si besoin : Supabase → <strong>Database</strong> → réinitialiser le{" "}
                    <strong>Database password</strong>, puis mets à jour partout (scripts, dashboard,
                    secrets GitHub).
                  </li>
                </ul>
              </div>
            )}
            {(errorMessage.includes("password authentication failed") ||
              errorMessage.includes('user "postgres"')) && (
              <div className="mt-4 rounded-lg border border-red-400/30 bg-black/30 p-4 text-sm leading-relaxed text-red-50/95">
                <p className="font-medium text-white">Pistes Supabase (pooler)</p>
                <ul className="mt-2 list-inside list-disc space-y-1 text-red-100/90">
                  <li>
                    Avec <code className="rounded bg-black/40 px-1">*.pooler.supabase.com</code>,
                    le user doit être{" "}
                    <code className="rounded bg-black/40 px-1">
                      postgres.&lt;référence_projet&gt;
                    </code>
                    , pas seulement <code className="rounded bg-black/40 px-1">postgres</code>.
                  </li>
                  <li>
                    Mot de passe = celui de la base dans Supabase (
                    <strong>Database password</strong>), réinitialisable sous Paramètres projet →
                    Database.
                  </li>
                  <li>
                    Compare avec{" "}
                    <code className="rounded bg-black/40 px-1">weather-benchmark/scripts/.env</code>{" "}
                    qui fonctionne déjà : mêmes{" "}
                    <code className="rounded bg-black/40 px-1">POSTGRES_USER</code> et{" "}
                    <code className="rounded bg-black/40 px-1">POSTGRES_PASSWORD</code> dans{" "}
                    <code className="rounded bg-black/40 px-1">dashboard/.env.local</code>.
                  </li>
                  <li>
                    Si tu utilises <code className="rounded bg-black/40 px-1">DATABASE_URL</code>,
                    vérifie qu&apos;elle est copiée depuis le dashboard Supabase (Session pooler),
                    sans espaces ni guillemets en trop.
                  </li>
                  <li>
                    Si le mot de passe contient <code className="rounded bg-black/40 px-1">#</code>{" "}
                    ou <code className="rounded bg-black/40 px-1">;</code>, mets la valeur entre{" "}
                    <strong>guillemets doubles</strong> dans{" "}
                    <code className="rounded bg-black/40 px-1">.env.local</code> — sinon le reste
                    est ignoré (commentaire) et Next.js peut retomber sur une{" "}
                    <code className="rounded bg-black/40 px-1">DATABASE_URL</code> avec user{" "}
                    <code className="rounded bg-black/40 px-1">postgres</code>.
                  </li>
                  <li>
                    Vérifie qu&apos;aucune variable <code className="rounded bg-black/40 px-1">DATABASE_URL</code>{" "}
                    n&apos;est définie au niveau Windows (Paramètres → Variables
                    d&apos;environnement) : elle prime parfois sur ce que tu crois lire dans le
                    fichier.
                  </li>
                </ul>
              </div>
            )}
          </div>
        )}

        {!errorMessage && !windowBounds && (
          <div className="rounded-2xl border border-white/15 bg-white/5 p-8 text-center">
            <p className="text-lg text-slate-200">Aucun score en base pour l&apos;instant</p>
            <p className="mt-2 text-sm text-slate-400">
              Lance le workflow GitHub (collecte quotidienne) pendant quelques jours, ou
              exécute <code className="rounded bg-black/30 px-1">compute_scores.py</code>{" "}
              en local une fois les prévisions et observations alignées.
            </p>
          </div>
        )}

        {!errorMessage && windowBounds && globalRows.length === 0 && (
          <div className="rounded-2xl border border-white/15 bg-white/5 p-8 text-center text-slate-300">
            Table <code className="text-sky-200">forecast_scores</code> vide pour la
            dernière fenêtre — même message : patience ou recalcul des scores.
          </div>
        )}

        {!errorMessage && globalRows.length > 0 && (
          <>
            <section className="space-y-4">
              <h2 className="text-xl font-semibold text-white">
                Classement global (MAE température moyenne)
              </h2>
              <p className="text-sm text-slate-400">
                Plus la MAE est basse, mieux c&apos;est. Précision pluie = part de bons
                jours sec/pluie ; Brier pluie = plus bas = mieux.
              </p>
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/50 shadow-xl shadow-sky-950/50">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400">
                      <th className="px-4 py-3 font-medium">Rang</th>
                      <th className="px-4 py-3 font-medium">Fournisseur</th>
                      <th className="px-4 py-3 font-medium">MAE T (°C)</th>
                      <th className="px-4 py-3 font-medium">RMSE T (°C)</th>
                      <th className="px-4 py-3 font-medium">MAE vent (m/s)</th>
                      <th className="px-4 py-3 font-medium">Préc. pluie</th>
                      <th className="px-4 py-3 font-medium">MAE pluie (mm)</th>
                      <th className="px-4 py-3 font-medium">Brier prob.</th>
                      <th className="px-4 py-3 font-medium">Échantillons</th>
                    </tr>
                  </thead>
                  <tbody>
                    {globalRows.map((r, i) => (
                      <tr
                        key={r.code}
                        className="border-b border-white/5 hover:bg-white/[0.04]"
                      >
                        <td className="px-4 py-3 font-mono text-sky-300">{i + 1}</td>
                        <td className="px-4 py-3">
                          <span className="font-medium text-white">{r.name}</span>
                          <span className="ml-2 font-mono text-xs text-slate-500">
                            {r.code}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-100">
                          {fmt(r.avgMaeTemp)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgRmseTemp)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgMaeWind)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmtPct(r.avgRainAcc)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgRainMae)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgBrier, 3)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-500">
                          {r.totalSamples}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="space-y-4">
              <h2 className="text-xl font-semibold text-white">
                Classement global (précision prédiction pluie sec / mouillé)
              </h2>
              <p className="text-sm text-slate-400">
                Part des jours où la prévision a le bon régime (&gt; seuil ou sec) pour
                l&apos;ensemble des villes et horizons — plus le pourcentage est élevé, mieux
                c&apos;est.
              </p>
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/50 shadow-xl shadow-sky-950/50">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400">
                      <th className="px-4 py-3 font-medium">Rang</th>
                      <th className="px-4 py-3 font-medium">Fournisseur</th>
                      <th className="px-4 py-3 font-medium">Préc. pluie</th>
                      <th className="px-4 py-3 font-medium">MAE T (°C)</th>
                      <th className="px-4 py-3 font-medium">RMSE T (°C)</th>
                      <th className="px-4 py-3 font-medium">MAE vent (m/s)</th>
                      <th className="px-4 py-3 font-medium">MAE pluie (mm)</th>
                      <th className="px-4 py-3 font-medium">Brier prob.</th>
                      <th className="px-4 py-3 font-medium">Échantillons</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortGlobalByRainAccDesc(globalRows).map((r, i) => (
                      <tr
                        key={`rain-${r.code}`}
                        className="border-b border-white/5 hover:bg-white/[0.04]"
                      >
                        <td className="px-4 py-3 font-mono text-sky-300">{i + 1}</td>
                        <td className="px-4 py-3">
                          <span className="font-medium text-white">{r.name}</span>
                          <span className="ml-2 font-mono text-xs text-slate-500">
                            {r.code}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono font-medium text-emerald-200/95">
                          {fmtPct(r.avgRainAcc)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgMaeTemp)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgRmseTemp)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgMaeWind)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgRainMae)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">
                          {fmt(r.avgBrier, 3)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-500">
                          {r.totalSamples}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="space-y-4">
              <h2 className="text-xl font-semibold text-white">MAE température par horizon</h2>
              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/50">
                <table className="w-full min-w-[880px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400">
                      <th className="px-3 py-3 font-medium">Fournisseur</th>
                      {horizons.map((h) => (
                        <th key={h} className="px-2 py-3 text-center font-medium">
                          J+{h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {horizonRows.map((row) => (
                      <tr
                        key={row.code}
                        className="border-b border-white/5 hover:bg-white/[0.04]"
                      >
                        <td className="px-3 py-2.5">
                          <span className="text-white">{row.name}</span>
                          <span className="ml-1 font-mono text-xs text-slate-500">
                            {row.code}
                          </span>
                        </td>
                        {horizons.map((h) => (
                          <td
                            key={h}
                            className="px-2 py-2.5 text-center font-mono text-slate-200"
                          >
                            {fmt(row.byHorizon[h])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="space-y-4">
              <h2 className="text-xl font-semibold text-white">
                Meilleur fournisseur par ville (MAE temp. moyenne)
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {cityRows.map((c) => (
                  <div
                    key={c.citySlug}
                    className="rounded-xl border border-white/10 bg-slate-900/40 p-4"
                  >
                    <p className="text-xs uppercase tracking-wide text-sky-400/90">
                      {c.cityName}
                    </p>
                    <p className="mt-1 text-lg font-medium text-white">
                      {c.bestProviderName}
                    </p>
                    <p className="font-mono text-xs text-slate-500">{c.bestProviderCode}</p>
                    <p className="mt-2 text-sm text-slate-400">
                      MAE T moy.{" "}
                      <span className="font-mono text-sky-200">{fmt(c.avgMaeTemp)} °C</span>
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-4">
              <h2 className="text-xl font-semibold text-white">
                Meilleur fournisseur par ville (précision pluie sec / mouillé)
              </h2>
              <p className="text-sm text-slate-400">
                Pour chaque ville : fournisseur avec la meilleure moyenne de précision binaire sur
                les horizons J+1…J+7 (même métrique que la colonne précision du tableau global).
              </p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {cityRainRows.map((c) => (
                  <div
                    key={`rain-${c.citySlug}`}
                    className="rounded-xl border border-white/10 bg-slate-900/40 p-4"
                  >
                    <p className="text-xs uppercase tracking-wide text-sky-400/90">
                      {c.cityName}
                    </p>
                    <p className="mt-1 text-lg font-medium text-white">
                      {c.bestProviderName}
                    </p>
                    <p className="font-mono text-xs text-slate-500">{c.bestProviderCode}</p>
                    <p className="mt-2 text-sm text-slate-400">
                      Précision pluie{" "}
                      <span className="font-mono text-emerald-200/95">
                        {fmtPct(c.avgRainAcc)}
                      </span>
                    </p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
