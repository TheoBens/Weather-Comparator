#!/usr/bin/env python3
import re
import sys
import urllib.request
from pathlib import Path

dart = Path(__file__).resolve().parents[2] / "meteo-app" / "lib" / "config" / "secrets.local.dart"
text = dart.read_text(encoding="utf-8")
url = re.search(r"supabaseUrl = '([^']+)'", text).group(1)
key = re.search(r"supabaseAnonKey =\s*'([^']+)'", text).group(1)
req = urllib.request.Request(
    f"{url}/rest/v1/cities?select=id,name&limit=1",
    headers={"apikey": key, "Authorization": f"Bearer {key}"},
)
with urllib.request.urlopen(req, timeout=15) as r:
    print(r.status, r.read().decode()[:200])
