#!/usr/bin/env python3
"""Génère lib/config/secrets.local.dart depuis scripts/.env ou Supabase CLI."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
ENV_FILE = REPO / "weather-benchmark" / "scripts" / ".env"
OUT = ROOT / "lib" / "config" / "secrets.local.dart"


def project_ref_from_env(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("POSTGRES_USER="):
            user = line.split("=", 1)[1].strip().strip('"')
            if user.startswith("postgres."):
                return user.split(".", 1)[1]
    m = re.search(r"postgres\.([a-z0-9]+)", text)
    return m.group(1) if m else None


def read_env_value(text: str, key: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def fetch_keys_via_cli(project_ref: str) -> tuple[str, str] | None:
    try:
        proc = subprocess.run(
            [
                "npx",
                "--yes",
                "supabase@latest",
                "projects",
                "api-keys",
                "--project-ref",
                project_ref,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            shell=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    publishable = None
    anon = None
    for item in data.get("keys", []):
        if item.get("type") == "publishable" and item.get("api_key"):
            publishable = item["api_key"]
        if item.get("id") == "anon" and item.get("api_key"):
            anon = item["api_key"]
    key = publishable or anon
    if not key:
        return None
    return f"https://{project_ref}.supabase.co", key


def write_secrets(url: str, key: str) -> None:
    content = f"""/// Fichier généré par `tool/sync_secrets.py` — ne pas committer.
class LocalSecrets {{
  LocalSecrets._();

  static const supabaseUrl = '{url}';
  static const supabaseAnonKey = '{key}';
}}
"""
    OUT.write_text(content, encoding="utf-8")
    print(f"Écrit {OUT.relative_to(ROOT)}")


def main() -> int:
    url = None
    key = None
    project_ref = None

    if ENV_FILE.is_file():
        env_text = ENV_FILE.read_text(encoding="utf-8")
        project_ref = project_ref_from_env(env_text)
        url = read_env_value(env_text, "SUPABASE_URL")
        key = read_env_value(env_text, "SUPABASE_ANON_KEY") or read_env_value(
            env_text, "SUPABASE_PUBLISHABLE_KEY"
        )
        if url and not url.startswith("http"):
            url = f"https://{url}"

    if project_ref and (not url or not key):
        cli = fetch_keys_via_cli(project_ref)
        if cli:
            url, key = cli

    if not project_ref and not url:
        print(
            "Impossible de déduire la config : renseignez weather-benchmark/scripts/.env "
            "ou connectez Supabase CLI (`npx supabase login`).",
            file=sys.stderr,
        )
        return 1

    if not url and project_ref:
        url = f"https://{project_ref}.supabase.co"

    if not key:
        print(
            "Clé publishable introuvable. Ajoutez SUPABASE_ANON_KEY dans scripts/.env "
            "ou lancez `npx supabase login` puis relancez ce script.",
            file=sys.stderr,
        )
        return 1

    write_secrets(url, key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
