"""Requêtes HTTP résilientes (timeouts SSL / réseau GitHub Actions vs APIs gratuites)."""
from __future__ import annotations

import time
from typing import Any, Mapping

import httpx


def httpx_get(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    timeout: httpx.Timeout | float | None = None,
    retries: int = 5,
    backoff_s: float = 3.0,
) -> httpx.Response:
    """
    GET avec nouvelles tentatives sur erreurs réseau / TLS souvent vues sur les runners CI.
    """
    if timeout is None:
        timeout = httpx.Timeout(120.0, connect=45.0)
    elif isinstance(timeout, (int, float)):
        timeout = httpx.Timeout(float(timeout), connect=min(45.0, float(timeout) / 2))

    last: BaseException | None = None
    for attempt in range(retries):
        try:
            r = httpx.get(url, params=params, timeout=timeout)
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
        except httpx.HTTPStatusError:
            raise
    assert last is not None
    raise last
