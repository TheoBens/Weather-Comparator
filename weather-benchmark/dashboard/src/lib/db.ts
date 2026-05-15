import postgres from "postgres";

let singleton: postgres.Sql | undefined;
let singletonKey = "";

function envFingerprint(): string {
  return [
    process.env.POSTGRES_HOST ?? "",
    process.env.POSTGRES_USER ?? "",
    process.env.POSTGRES_PASSWORD ?? "",
    process.env.POSTGRES_DB ?? "",
    process.env.POSTGRES_PORT ?? "",
    process.env.DATABASE_URL ?? "",
  ].join("\0");
}

/**
 * Sur le pooler Supabase, l'utilisateur dans une URI ne doit pas être « postgres » seul.
 */
function assertPoolerUrlIfApplicable(connectionUrl: string): void {
  const normalized = connectionUrl.trim().replace(/^postgres:\/\//i, "postgresql://");
  let hostname = "";
  let username = "";
  try {
    const u = new URL(normalized);
    hostname = u.hostname;
    username = decodeURIComponent(u.username || "");
  } catch {
    return;
  }
  if (!hostname.includes("pooler.supabase.com")) return;
  if (username === "postgres") {
    throw new Error(
      "DATABASE_URL : sur *.pooler.supabase.com, le user dans l'URI doit être postgres.<référence>, " +
        "pas « postgres » seul. Recopie l'URI « Session pooler » depuis Supabase, " +
        "ou utilise POSTGRES_HOST + POSTGRES_USER + POSTGRES_PASSWORD (et supprime / comment la ligne DATABASE_URL).",
    );
  }
}

/**
 * Connexion Postgres — alignée sur les scripts Python.
 * Ne pas utiliser `postgres` seul comme user avec *.pooler.supabase.com.
 */
export function getDb(): postgres.Sql | null {
  const fp = envFingerprint();
  if (singleton && singletonKey !== fp) {
    void singleton.end({ timeout: 3 }).catch(() => {});
    singleton = undefined;
  }
  singletonKey = fp;

  if (singleton) return singleton;

  const host =
    process.env.POSTGRES_HOST?.trim() ||
    process.env.SUPABASE_DB_HOST?.trim();
  const password =
    process.env.POSTGRES_PASSWORD?.trim() ||
    process.env.SUPABASE_DB_PASSWORD?.trim();

  if (host && !password) {
    throw new Error(
      "POSTGRES_PASSWORD manquant ou vide alors que POSTGRES_HOST est défini — " +
        "dans `.env.local`, un `#` sans guillemets coupe la valeur (mot de passe tronqué). " +
        'Ex. POSTGRES_PASSWORD="mon#motDePasse". ' +
        "Sinon vérifie qu’aucune DATABASE_URL système Windows n’entre en jeu.",
    );
  }

  if (host && password) {
    const userExplicit =
      process.env.POSTGRES_USER?.trim() ||
      process.env.SUPABASE_DB_USER?.trim() ||
      "";
    const isPooler = host.includes("pooler.supabase.com");

    const user = userExplicit || (isPooler ? "" : "postgres");

    if (!user) {
      throw new Error(
        "POSTGRES_USER manquant : avec le pooler Supabase, définissez POSTGRES_USER=postgres.<référence_projet> (Database → Session pooler).",
      );
    }
    if (isPooler && user === "postgres") {
      throw new Error(
        'POSTGRES_USER ne doit pas être « postgres » seul avec *.pooler.supabase.com ; utilisez postgres.<référence_projet> (ex. postgres.abcd1234).',
      );
    }

    const database =
      process.env.POSTGRES_DB?.trim() ||
      process.env.SUPABASE_DB_NAME?.trim() ||
      "postgres";
    const port = Number.parseInt(
      process.env.POSTGRES_PORT?.trim() ||
        process.env.SUPABASE_DB_PORT?.trim() ||
        "5432",
      10,
    );
    singleton = postgres({
      host,
      port,
      user,
      password,
      database,
      ssl: "require",
      max: 2,
      idle_timeout: 20,
      connect_timeout: 45,
    });
    return singleton;
  }

  const url = process.env.DATABASE_URL?.trim();
  if (!url) return null;

  assertPoolerUrlIfApplicable(url);

  singleton = postgres(url, {
    max: 2,
    idle_timeout: 20,
    connect_timeout: 45,
  });
  return singleton;
}
