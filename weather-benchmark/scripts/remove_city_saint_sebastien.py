#!/usr/bin/env python3
"""Applique supabase/remove_city_saint_sebastien.sql puis recalcule les scores équitables."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import lib.config  # noqa: F401
from lib.config import database_url

SQL = ROOT.parent / "supabase" / "remove_city_saint_sebastien.sql"


def main() -> None:
    if not SQL.is_file():
        raise SystemExit(f"Fichier introuvable: {SQL}")
    sql = SQL.read_text(encoding="utf-8")
    with psycopg.connect(database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
    print("SQL appliqué:", SQL)

    print("Recalcul des scores équitables…")
    subprocess.run(
        [sys.executable, str(ROOT / "compute_fair_scores.py")],
        cwd=str(ROOT),
        check=True,
    )


if __name__ == "__main__":
    main()
