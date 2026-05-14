import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo

_ENV_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_ENV_DIR / ".env")


def database_url() -> str:
    """
    Retourne une chaîne utilisable par psycopg.connect().

    Si le mot de passe contient @, :, #, etc., préférer POSTGRES_* plutôt que DATABASE_URL.
    """
    host = os.getenv("POSTGRES_HOST") or os.getenv("SUPABASE_DB_HOST")
    password = os.getenv("POSTGRES_PASSWORD") or os.getenv("SUPABASE_DB_PASSWORD")
    if host and password:
        user = os.getenv("POSTGRES_USER") or os.getenv("SUPABASE_DB_USER") or "postgres"
        dbname = os.getenv("POSTGRES_DB") or os.getenv("SUPABASE_DB_NAME") or "postgres"
        port = int(os.getenv("POSTGRES_PORT") or os.getenv("SUPABASE_DB_PORT") or "5432")
        sslmode = os.getenv("POSTGRES_SSLMODE") or "require"
        return make_conninfo(
            host=host,
            user=user,
            password=password,
            dbname=dbname,
            port=port,
            sslmode=sslmode,
        )
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    raise RuntimeError(
        "Configurer DATABASE_URL ou (POSTGRES_HOST + POSTGRES_PASSWORD). Voir .env.example"
    )
