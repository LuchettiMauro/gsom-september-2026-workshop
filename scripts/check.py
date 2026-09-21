"""Phase 0 readiness check.

    uv run python scripts/check.py

Verifies every prerequisite by actually using it — a key that parses but does
not work is exactly the failure this exists to catch. So it makes a real
(3-token) Gemini call and writes a real Langfuse trace rather than checking
that the strings are non-empty.

Prints one line to paste into a Phase 0 issue on GitHub.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from stargate.config import DOCS_DIR, PARQUET, settings  # noqa: E402

REPO = "LuchettiMauro/gsom-september-2026-workshop"

Result = tuple[str, str, str]  # (label, value, detail)

OK = "ok"


def _version_of(command: str, *args: str) -> str | None:
    exe = shutil.which(command)
    if exe is None:
        return None
    try:
        out = subprocess.run([exe, *args], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (out.stdout or out.stderr).strip().splitlines()
    if not text:
        return None
    parts = text[0].split()
    return parts[1] if len(parts) > 1 else text[0]


# --- individual checks -----------------------------------------------------


def check_uv() -> Result:
    version = _version_of("uv", "--version")
    return (
        "uv",
        version or "MISSING",
        "" if version else "uv ships in the Codespace image — rebuild the container (F1, "
        "Codespaces: Rebuild Container).",
    )


def check_python() -> Result:
    v = sys.version_info
    value = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) < (3, 11):
        return ("python", f"{value} TOO-OLD", "Run through `uv run`, which supplies Python 3.12.")
    return ("python", value, "")


def check_marimo() -> Result:
    found = importlib.util.find_spec("marimo") is not None
    return ("marimo", OK if found else "MISSING", "" if found else "Run `uv sync`.")


def check_serve() -> Result:
    """The extra that session 2 runs on.

    Agno keeps its Telegram interface behind `agno[telegram]`, and a missing
    piece here does not show up until notebook 09 fails at import — in the
    room, halfway through the second session.
    """
    missing = [
        name for name in ("fastapi", "uvicorn", "telebot") if importlib.util.find_spec(name) is None
    ]
    if missing:
        return (
            "serve",
            "MISSING",
            "Needed in session 2 — run `uv sync --extra serve`. Not fatal for session 1.",
        )
    return ("serve", OK, "")


# Where the .deb in .devcontainer/setup.sh puts the binary. A terminal opened
# mid-build does not see it on PATH yet, and reporting MISSING on a container
# that has it sends the student off installing something they already have.
CLOUDFLARED_FALLBACKS = (
    Path("/usr/local/bin/cloudflared"),
    Path("/usr/bin/cloudflared"),
)


def check_cloudflared() -> Result:
    version = _version_of("cloudflared", "--version")
    if version is None:
        installed = next((p for p in CLOUDFLARED_FALLBACKS if p.exists()), None)
        if installed is not None:
            return (
                "cloudflared",
                OK,
                f"installed at {installed}, but not on this terminal's PATH — "
                "close and reopen the terminal before session 2.",
            )
        return (
            "cloudflared",
            "MISSING",
            "Needed in session 2, and it ships in the Codespace image — rebuild the "
            "container (F1, Codespaces: Rebuild Container). Not fatal for session 1.",
        )
    return ("cloudflared", OK, "")


def check_data() -> Result:
    """Present and usable, rather than complete.

    A partial corpus is worth saying out loud and is not worth failing over:
    the workshop reads whatever is on disk, and a document the reading room
    refused during the build comes back on the next fetch.
    """
    docs = len(list(DOCS_DIR.glob("*.md"))) if DOCS_DIR.exists() else 0
    if docs == 0 or not PARQUET.exists():
        return ("data", "MISSING", "Run `uv run python scripts/fetch_data.py`.")

    manifest = DOCS_DIR.parent / "corpus_manifest.json"
    try:
        expected = len(json.loads(manifest.read_text(encoding="utf-8"))["documents"])
    except (OSError, ValueError, KeyError):
        expected = docs
    if docs < expected:
        return (
            "data",
            OK,
            f"{docs} of {expected} documents, sightings parquet present — "
            "`uv run python scripts/fetch_data.py` fetches the rest",
        )
    return ("data", OK, f"{docs} documents, sightings parquet present")


def _suggest_models(client: Any, limit: int = 6) -> str:
    """Model names this key can actually use, for when the configured one is gone."""
    try:
        names = [
            m.name.removeprefix("models/")
            for m in client.models.list()
            if "generateContent" in (getattr(m, "supported_actions", None) or [])
        ]
    except Exception:
        return ""
    flash = [n for n in names if "flash" in n and "preview" not in n]
    pick = flash[:limit] or names[:limit]
    if not pick:
        return ""
    return " Models your key can see: " + ", ".join(pick) + "."


def _is_overloaded(exc: Exception) -> bool:
    """503 / UNAVAILABLE: Google is busy. It says nothing about the key."""
    text = str(exc).lower()
    return "503" in text or "unavailable" in text or "overloaded" in text or "high demand" in text


def check_gemini() -> Result:
    """One real call. Costs about three tokens.

    Free-tier Gemini returns 503 under load often enough that a whole cohort
    checking in on the same evening will see it. Retrying twice turns most of
    those into a pass, and the ones left say plainly that it is Google's
    problem rather than the student's key.
    """
    cfg = settings()
    if not cfg.google_api_key:
        return (
            "gemini",
            "MISSING",
            "GOOGLE_API_KEY not set — see PHASE0.md, *Get a Google AI Studio key*.",
        )
    client: Any = None
    for attempt in range(3):
        try:
            from google import genai

            client = genai.Client(api_key=cfg.google_api_key)
            response = client.models.generate_content(
                model=cfg.model, contents="Reply with the single word: ready"
            )
            if not getattr(response, "text", None):
                return ("gemini", "FAILED", "The API returned an empty response.")
            return ("gemini", OK, f"model {cfg.model}")
        except Exception as exc:
            if _is_overloaded(exc) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            detail = f"{type(exc).__name__}: {str(exc)[:160]}"
            text = str(exc).lower()
            if _is_overloaded(exc):
                detail = (
                    "Google's servers are busy (503). Your key is fine — this is load on "
                    "their side. Wait a few minutes and run the check again."
                )
            elif "no longer available" in text or "not found" in text or "404" in text:
                detail = (
                    f"{cfg.model} is not available to this key — Google has retired it for "
                    f"new projects. Set STARGATE_MODEL in .env to a current model."
                    + (_suggest_models(client) if client is not None else "")
                )
            return ("gemini", "FAILED", detail)
    return ("gemini", "FAILED", "Unreachable.")


def check_langfuse() -> Result:
    """Authenticate and write one real trace, then print its URL.

    Deliberately drives the Langfuse SDK itself rather than going through
    `stargate.observability`: that module arrives in notebook 04, so it is
    absent from the early `step-*` checkpoints, and this check has to run
    wherever a student happens to be standing.
    """
    cfg = settings()
    if not cfg.langfuse_configured:
        return ("langfuse", "MISSING", "Keys not set — see PHASE0.md, *Get a Langfuse account*.")
    try:
        # The SDK reads its credentials from the environment, not from arguments.
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", cfg.langfuse_public_key or "")
        os.environ.setdefault("LANGFUSE_SECRET_KEY", cfg.langfuse_secret_key or "")
        os.environ.setdefault("LANGFUSE_HOST", cfg.langfuse_host)

        from langfuse import get_client

        client = get_client()
        if client is None:
            return ("langfuse", "FAILED", "Could not create a client.")
        if not client.auth_check():
            return ("langfuse", "FAILED", "Credentials rejected. Check both keys and the region.")
        with client.start_as_current_observation(name="phase-0-check") as span:
            span.update(input="phase 0", output="ready")
            url = client.get_trace_url(trace_id=span.trace_id)
        client.flush()
    except Exception as exc:
        text = f"{type(exc).__name__} {exc}".lower()
        if "unauthorized" in text or "401" in text or "403" in text:
            return (
                "langfuse",
                "FAILED",
                "Credentials rejected. Check both keys, and that the account is on the "
                "EU region — the plain cloud.langfuse.com, which is what .env expects.",
            )
        return ("langfuse", "FAILED", f"{type(exc).__name__}: {str(exc)[:160]}")
    return ("langfuse", OK, f"trace written: {url}")


def check_fastembed() -> Result:
    """Download and run the embedding model, so it is cached before the session."""
    try:
        from fastembed import TextEmbedding

        from stargate.config import DEFAULT_EMBEDDER

        model = TextEmbedding(model_name=DEFAULT_EMBEDDER)
        vector = next(iter(model.embed(["remote viewing"])))
    except Exception as exc:
        return ("fastembed", "FAILED", f"{type(exc).__name__}: {str(exc)[:160]}")
    return ("fastembed", OK, f"{len(vector)}-dimensional vectors, cached locally")


def check_telegram() -> Result:
    cfg = settings()
    if not cfg.telegram_token:
        return (
            "telegram",
            "MISSING",
            "Needed in session 2 — see PHASE0.md, *Get a Telegram bot token*.",
        )
    try:
        import httpx

        response = httpx.get(f"https://api.telegram.org/bot{cfg.telegram_token}/getMe", timeout=20)
        payload = response.json()
        if not payload.get("ok"):
            return ("telegram", "FAILED", str(payload.get("description", ""))[:120])
        username = payload["result"].get("username", "?")
    except Exception as exc:
        return ("telegram", "FAILED", f"{type(exc).__name__}: {str(exc)[:160]}")
    return ("telegram", OK, f"@{username}")


def issue_url(ready_line: str) -> str:
    """A Phase 0 issue with the READY line already in it.

    The line is only `label=value` pairs — no keys, no trace URLs, no bot
    name — so it is safe to post on a public repository.
    """
    query = urlencode({"template": "phase-0.yml", "ready": ready_line})
    return f"https://github.com/{REPO}/issues/new?{query}"


CHECKS: tuple[Callable[[], Result], ...] = (
    check_uv,
    check_python,
    check_marimo,
    check_serve,
    check_data,
    check_gemini,
    check_langfuse,
    check_fastembed,
    check_telegram,
    check_cloudflared,
)

# Session 1 cannot start without these. The rest can be fixed later.
ESSENTIAL = {"uv", "python", "marimo", "data", "gemini", "langfuse", "fastembed"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="print only the READY line")
    args = parser.parse_args()

    if args.quiet:
        os.environ.setdefault("STARGATE_QUIET", "1")

    results: list[Result] = []
    for check in CHECKS:
        label, value, detail = check()
        results.append((label, value, detail))
        if not args.quiet:
            mark = " " if value not in {"MISSING", "FAILED"} and "TOO-OLD" not in value else "!"
            print(f"{mark} {label:<12} {value}")
            if detail:
                print(f"    {detail}")

    broken = [label for label, value, _ in results if value in {"MISSING", "FAILED"}]
    blocking = [label for label in broken if label in ESSENTIAL]

    summary = "  ".join(f"{label}={value}" for label, value, _ in results)
    ready_line = f"READY  {summary}"
    print()
    print(ready_line)
    print()
    print("Post that line as a Phase 0 issue — this link has it filled in already:")
    print(f"    {issue_url(ready_line)}")
    print("Do it even if something failed. That is what the three days are for.")

    if blocking:
        print()
        print(f"Not ready yet: {', '.join(blocking)}. See TROUBLESHOOTING.md.")
        return 1
    if broken:
        print()
        print(f"Fine for session 1; fix before session 2: {', '.join(broken)}")
    print()
    print("Session 1 starts here — run this in a terminal, from the repo root:")
    print("    uv run marimo edit --no-token")
    print("then open notebooks/01_chat_completions.py from the page that appears.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
