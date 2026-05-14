const CRITERIA = [
  "Probabilité / intempéries (précision pluie, indicateurs nuages / orages)",
  "Température (erreur moyenne et quadratique)",
  "Vent (erreur sur la vitesse)",
];

const CITIES = [
  "Paris",
  "Bordeaux",
  "Toulouse",
  "Lyon",
  "Marseille",
  "Nantes",
  "Lille",
  "Limoges",
  "Besançon",
  "Brest",
  "Nice",
  "Strasbourg",
  "Clermont-Ferrand",
];

const PROVIDERS = [
  "Open-Meteo",
  "Météo-France Open Data",
  "OpenWeatherMap",
  "WeatherAPI",
  "Tomorrow.io",
  "Visual Crossing",
  "Meteostat",
  "Foreca",
];

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-950 via-slate-900 to-slate-950 text-slate-100">
      <main className="mx-auto flex max-w-4xl flex-col gap-12 px-6 py-16">
        <header className="space-y-4">
          <p className="text-sm font-medium uppercase tracking-widest text-sky-300">
            Bench comparatif
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Météos comparateur
          </h1>
          <p className="max-w-2xl text-lg leading-relaxed text-slate-300">
            Classement des services météo selon le pourcentage et le type de bonnes
            prédictions (J+1 à J+7), par ville et par variable.
          </p>
        </header>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
          <h2 className="mb-4 text-lg font-semibold text-white">Critères suivis</h2>
          <ul className="list-inside list-disc space-y-2 text-slate-300">
            {CRITERIA.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-slate-400">
            Précipitations : précision de classification (pluie / sec) et erreur sur la
            quantité ; probabilité de pluie évaluée via le score de Brier.
          </p>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
            <h2 className="mb-3 text-lg font-semibold text-white">Villes</h2>
            <ul className="columns-2 gap-4 text-sm text-slate-300">
              {CITIES.map((city) => (
                <li key={city} className="break-inside-avoid py-0.5">
                  {city}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
            <h2 className="mb-3 text-lg font-semibold text-white">Fournisseurs</h2>
            <ul className="space-y-1 text-sm text-slate-300">
              {PROVIDERS.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="rounded-2xl border border-dashed border-sky-400/40 bg-sky-950/30 p-6">
          <h2 className="mb-2 text-lg font-semibold text-white">Branchement données</h2>
          <p className="text-sm leading-relaxed text-slate-300">
            Les scripts Python alimentent PostgreSQL (Supabase). Ce tableau de bord
            pourra interroger la base via l’URL et la clé Supabase (variables{" "}
            <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs text-sky-200">
              NEXT_PUBLIC_SUPABASE_URL
            </code>{" "}
            et clé serveur / route API). Configurez le secret GitHub{" "}
            <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
              DATABASE_URL
            </code>{" "}
            pour la collecte planifiée.
          </p>
        </section>
      </main>
    </div>
  );
}
