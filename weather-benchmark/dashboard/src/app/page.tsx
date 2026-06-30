import { DashboardRankings } from "@/components/DashboardRankings";
import { getDb } from "@/lib/db";
import {
  fetchCityProviderMetrics,
  fetchGlobalLeaderboard,
  fetchHorizonMatrix,
  fetchLatestScoreWindow,
} from "@/lib/scores";

export const dynamic = "force-dynamic";

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
  let cityMetricRows: Awaited<ReturnType<typeof fetchCityProviderMetrics>> = [];

  try {
    windowBounds = await fetchLatestScoreWindow(sql);
    if (windowBounds) {
      const { start: wStart, end: wEnd } = windowBounds;
      [globalRows, horizonRows, cityMetricRows] = await Promise.all([
        fetchGlobalLeaderboard(sql, wStart, wEnd),
        fetchHorizonMatrix(sql, wStart, wEnd),
        fetchCityProviderMetrics(sql, wStart, wEnd),
      ]);
    }
  } catch (e) {
    errorMessage = e instanceof Error ? e.message : String(e);
  }

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
            <DashboardRankings
              globalRows={globalRows}
              cityMetricRows={cityMetricRows}
              horizonRows={horizonRows}
            />
          </>
        )}
      </main>
    </div>
  );
}
