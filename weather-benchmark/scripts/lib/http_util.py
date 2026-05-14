"""Requêtes HTTP résilientes (timeouts SSL / réseau GitHub Actions vs APIs gratuites)."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Any, Mapping
from urllib.parse import urlencode

import httpx

# Réutiliser un Client pour plusieurs GET vers le même hôte évite une poignée TLS par ville (CI GitHub).
DEFAULT_ARCHIVE_TIMEOUT = httpx.Timeout(180.0, connect=90.0)


def archive_client() -> httpx.Client:
    return httpx.Client(
        timeout=DEFAULT_ARCHIVE_TIMEOUT,
        http2=False,
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=10),
        headers={"User-Agent": "weather-benchmark/1.0 (collect; +https://open-meteo.com)"},
    )


def _flatten_query(params: Mapping[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for key, val in params.items():
        if isinstance(val, (list, tuple)):
            for item in val:
                pairs.append((key, str(item)))
        elif val is None:
            continue
        else:
            pairs.append((key, str(val)))
    return pairs


def build_url(url: str, params: Mapping[str, Any] | None) -> str:
    if not params:
        return url
    return url + "?" + urlencode(_flatten_query(params))


def curl_get_body(url_with_query: str) -> str:
    """Fallback TLS : curl utilise une pile différente de Python/httpx (souvent plus fiable sur les runners GH)."""
    curl_exe = shutil.which("curl")
    if not curl_exe:
        raise RuntimeError("curl introuvable dans le PATH")
    proc = subprocess.run(
        [
            curl_exe,
            "-sS",
            "-L",
            "--compressed",
            "--connect-timeout",
            "90",
            "--max-time",
            "240",
            "-H",
            "User-Agent: weather-benchmark/1.1 (+open-meteo)",
            url_with_query,
        ],
        capture_output=True,
        text=True,
        timeout=260,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or "").strip() or proc.stdout[:500]
        raise RuntimeError(f"curl exit {proc.returncode}: {err}")
    return proc.stdout


def http_get_json_with_curl_fallback(
    url: str,
    params: Mapping[str, Any] | None = None,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """
    GET JSON ; en cas d'échec TLS/connexion avec httpx, retente via curl (présent sur ubuntu-latest).
    """
    try:
        r = httpx_get(url, params=params, client=client)
        return r.json()
    except (
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.ConnectError,
        httpx.RemoteProtocolError,
    ):
        full = build_url(url, params or {})
        return json.loads(curl_get_body(full))


def httpx_get(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    timeout: httpx.Timeout | float | None = None,
    retries: int = 8,
    backoff_s: float = 5.0,
    client: httpx.Client | None = None,
) -> httpx.Response:
    """
    GET avec nouvelles tentatives sur erreurs réseau / TLS souvent vues sur les runners CI.
    Si ``client`` est fourni (ex. ``archive_client()``), les connexions sont réutilisées.
    """
    if timeout is None:
        timeout = DEFAULT_ARCHIVE_TIMEOUT
    elif isinstance(timeout, (int, float)):
        timeout = httpx.Timeout(float(timeout), connect=min(90.0, float(timeout) / 2))

    getter = client.get if client is not None else httpx.get
    last: BaseException | None = None
    for attempt in range(retries):
        try:
            r = getter(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.WriteError,
        ) as e:
            last = e
            if attempt < retries - 1:
                time.sleep(backoff_s * (attempt + 1))
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code in (502, 503, 504, 429, 529) and attempt < retries - 1:
                last = e
                time.sleep(backoff_s * (attempt + 1))
                continue
            raise
    assert last is not None
    raise last
