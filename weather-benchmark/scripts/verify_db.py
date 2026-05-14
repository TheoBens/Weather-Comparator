#!/usr/bin/env python3
"""Teste DATABASE_URL : connexion SSL + présence des tables du bench."""
from __future__ import annotations

import os
import sys

import psycopg

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lib.config  # noqa: F401
from lib.config import database_url

EXPECTED = (
    "cities",
    "providers",
    "ingest_runs",
    "forecasts",
    "observations",
    "forecast_scores",
)


def main() -> None:
    url = database_url()
    if "sslmode=" not in url and "supabase" in url:
        print(
            "Astuce : si la connexion échoue, ajoute ?sslmode=require à la fin de DATABASE_URL."
        )
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            one = cur.fetchone()
            if one is None or one[0] != 1:
                raise RuntimeError("SELECT 1 inattendu")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = ANY(%s)
                ORDER BY table_name
                """,
                (list(EXPECTED),),
            )
            found = {r[0] for r in cur.fetchall()}
    missing = [t for t in EXPECTED if t not in found]
    if missing:
        print("ECHEC — tables manquantes:", ", ".join(missing))
        print("  Lance: python apply_schema.py")
        raise SystemExit(1)
    print("OK — connexion PostgreSQL et", len(found), "tables attendues presentes.")


if __name__ == "__main__":
    main()
