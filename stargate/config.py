"""Settings, read once from the environment.

Importing this module must never fail, even with an empty `.env` — the test
suite and parts of `scripts/check.py` run without any keys at all. Missing
credentials are reported when something actually tries to use them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
PARQUET = DATA_DIR / "nuforc.parquet"
LANCEDB_DIR = REPO_ROOT / "lancedb"
SESSION_DB = REPO_ROOT / "stargate.db"

# Where the embedding model is cached. FastEmbed's own default is the system
# temp directory, which Linux cleans out and a container image does not carry
# over — either way the 80 MB download silently happens again. Pinning it
# inside the repo (git-ignored) makes it survive reboots, Codespaces restarts
# and the devcontainer prebuild. Set before anything imports fastembed, and
# only if the environment has not already chosen.
EMBED_CACHE_DIR = DATA_DIR / ".cache"
os.environ.setdefault("FASTEMBED_CACHE_PATH", str(EMBED_CACHE_DIR))

# The workshop default. The lite models get the highest free-tier allowance,
# 15 requests/minute against 10 for the full flash models, and a single agent
# question can cost six or more calls.
#
# Google retires Gemini models faster than this repo is updated: once a model is
# deprecated it keeps working for existing projects but new API keys get
# "no longer available to new users". If that happens, set STARGATE_MODEL in
# `.env` to a current model — `uv run python scripts/check.py` prints the ones
# your key can actually see.
DEFAULT_MODEL = "gemini-3.1-flash-lite"

# FastEmbed's small English model: ~80 MB, CPU-only, no API and therefore no
# rate limit. Pre-downloaded during phase 0.
DEFAULT_EMBEDDER = "BAAI/bge-small-en-v1.5"


class MissingCredential(RuntimeError):
    """Raised when something needs a key that is not in the environment."""


@dataclass(frozen=True)
class Settings:
    google_api_key: str | None
    openai_api_key: str | None
    anthropic_api_key: str | None
    langfuse_public_key: str | None
    langfuse_secret_key: str | None
    langfuse_host: str
    telegram_token: str | None
    telegram_webhook_secret: str | None
    telegram_allowed_chat_ids: frozenset[int]
    model: str
    count_calls: bool

    @property
    def langfuse_configured(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    @property
    def telegram_restricted(self) -> bool:
        """True when only the listed chats may talk to the bot."""
        return bool(self.telegram_allowed_chat_ids)

    def telegram_chat_allowed(self, chat_id: int) -> bool:
        return not self.telegram_allowed_chat_ids or chat_id in self.telegram_allowed_chat_ids

    def require_google(self) -> str:
        if not self.google_api_key:
            raise MissingCredential(
                "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key "
                "from https://aistudio.google.com/apikey (free, no credit card)."
            )
        return self.google_api_key


def _chat_ids(raw: str | None) -> frozenset[int]:
    """Parse TELEGRAM_ALLOWED_CHAT_IDS: a comma-separated list, blanks ignored.

    Anything that is not a number is dropped rather than raised on: a typo in
    `.env` should not stop the bot from starting, it should show up as a chat
    that cannot talk to it.
    """
    if not raw:
        return frozenset()
    ids = set()
    for piece in raw.replace(";", ",").split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            ids.add(int(piece))
        except ValueError:
            continue
    return frozenset(ids)


def _load_dotenv_once() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is a hard dependency
        return
    load_dotenv(REPO_ROOT / ".env", override=False)


@lru_cache(maxsize=1)
def settings() -> Settings:
    """The process-wide settings. Cached, so `.env` is read once."""
    _load_dotenv_once()
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY") or None,
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY") or None,
        langfuse_host=os.getenv("LANGFUSE_HOST") or "https://cloud.langfuse.com",
        telegram_token=os.getenv("TELEGRAM_TOKEN") or None,
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN") or None,
        telegram_allowed_chat_ids=_chat_ids(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS")),
        model=os.getenv("STARGATE_MODEL") or DEFAULT_MODEL,
        count_calls=os.getenv("STARGATE_COUNT_CALLS", "1") not in {"0", "false", "False", ""},
    )
