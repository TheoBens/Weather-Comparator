"""Requêtes HTTP résilientes (timeouts SSL / réseau GitHub Actions vs APIs gratuites)."""
from __future__ import annotations

import time
from typing import Any, Mapping

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
