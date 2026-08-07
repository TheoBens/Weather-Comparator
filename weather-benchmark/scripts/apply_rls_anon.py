#!/usr/bin/env python3
"""Applique meteo-app/supabase/rls_read_anon.sql (GRANT + RLS pour role anon)."""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg

SCRIPTS = Path(__file__).resolve().parents[2] / "weather-benchmark" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import lib.config  # noqa: F401
from lib.config import database_url

REPO = Path(__file__).resolve().parents[2]
SQL_FILE = REPO / "meteo-app" / "supabase" / "rls_read_anon.sql"


def main() -> None:
    if not SQL_FILE.is_file():
        raise SystemExit(f"Fichier introuvable: {SQL_FILE}")
    sql = SQL_FILE.read_text(encoding="utf-8")
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
    print("RLS + GRANT anon appliqués:", SQL_FILE)


if __name__ == "__main__":
    main()
