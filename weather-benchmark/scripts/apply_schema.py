#!/usr/bin/env python3
"""Applique weather-benchmark/supabase/schema.sql sur la base pointee par DATABASE_URL."""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import lib.config  # noqa: F401
from lib.config import database_url

SCHEMA = ROOT.parent / "supabase" / "schema.sql"


def main() -> None:
    if not SCHEMA.is_file():
        raise SystemExit(f"Fichier schema introuvable: {SCHEMA}")
    sql = SCHEMA.read_text(encoding="utf-8")
    url = database_url()
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
    print("Schema applique:", SCHEMA)


if __name__ == "__main__":
    main()
