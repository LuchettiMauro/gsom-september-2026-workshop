"""Tracing, switched on in notebook 04 and left on for the rest of the course.

This is wired up early on purpose. By session 2 every student has a week of
real traces from their own questions — which is the dataset the entire
evaluation block runs on. Turning observability on at the end, once you already
know what you built, teaches the wrong order.

Three lines of setup, then every agent run shows up in Langfuse automatically.
"""

from __future__ import annotations

import os
from typing import Any

from stargate.config import settings

_instrumented = False


def enable_tracing(*, quiet: bool = False) -> Any | None:
    """Send every Agno agent run to Langfuse.

    Safe to call repeatedly — notebooks get re-run constantly and double
    instrumentation produces duplicate spans.

    Returns the Langfuse client, or None if no credentials are configured
    (in which case the notebooks still work, they just aren't traced).
    """
    global _instrumented

    cfg = settings()
    if not cfg.langfuse_configured:
        if not quiet:
            print(
                "Langfuse keys not set — running untraced.\n"
                "Add LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to .env to fix."
            )
        return None

    # The Langfuse SDK reads these from the environment.
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", cfg.langfuse_public_key or "")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", cfg.langfuse_secret_key or "")
    os.environ.setdefault("LANGFUSE_HOST", cfg.langfuse_host)

    from langfuse import get_client

    client = get_client()

    if not _instrumented:
        from openinference.instrumentation.agno import AgnoInstrumentor

        AgnoInstrumentor().instrument()
        _instrumented = True

    if not quiet:
        print(f"Tracing to {cfg.langfuse_host}")
    return client


def check_connection() -> bool:
    """Verify the Langfuse credentials actually work. Used by scripts/check.py."""
    client = enable_tracing(quiet=True)
    if client is None:
        return False
    result = client.auth_check()
    return bool(result)


def flush() -> None:
    """Push buffered spans immediately.

    Notebooks exit before the background exporter fires, so without this a
    student's last few runs never arrive and they conclude tracing is broken.
    """
    cfg = settings()
    if not cfg.langfuse_configured:
        return
    from langfuse import get_client

    get_client().flush()
