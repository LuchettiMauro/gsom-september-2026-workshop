#!/usr/bin/env bash
# Runs once, when the container is built — and, because this repo has
# prebuilds turned on, usually on GitHub's machines rather than on a student's
# Codespace. Everything expensive belongs here.
set -euo pipefail

echo "--- uv"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "--- cloudflared"
# Session 2 gives the agent a public address with a tunnel. Installing it here
# is the whole reason a Codespace skips two steps of Phase 0.
arch="$(dpkg --print-architecture)"
curl -fsSL -o /tmp/cloudflared.deb \
  "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}.deb"
sudo dpkg -i /tmp/cloudflared.deb
rm -f /tmp/cloudflared.deb

echo "--- dependencies"
# `serve` too: session 2 needs FastAPI, uvicorn and the Telegram interface,
# and nobody should discover that halfway through the session.
uv sync --extra serve

echo "--- corpus"
# Deliberately not fatal. This script is the onCreateCommand and runs under
# `set -e`: a non-zero exit here fails container creation outright, and
# Codespaces replaces the container with a recovery image on Alpine that has
# no toolchain, no corpus, and none of the ports devcontainer.json forwards.
# One document the reading room refuses today is not worth that.
if ! uv run python scripts/fetch_data.py; then
  echo
  echo "WARNING: the corpus is incomplete, and the container is otherwise fine."
  echo "         The workshop runs on what did download. To retry the rest:"
  echo "             uv run python scripts/fetch_data.py"
fi

echo "--- embedding model"
# ~80 MB from Hugging Face. FASTEMBED_CACHE_PATH puts it under data/.cache so
# it survives into the image, and out the other side of a Codespace restart.
export FASTEMBED_CACHE_PATH="${PWD}/data/.cache"
uv run python -c "
from stargate.config import DEFAULT_EMBEDDER
from fastembed import TextEmbedding
next(iter(TextEmbedding(model_name=DEFAULT_EMBEDDER).embed(['warm the cache'])))
print('cached')
"

echo "--- .env"
# Left empty on purpose: the four keys are the one part of Phase 0 that no
# image can do for you.
cp -n .env.example .env || true

echo
echo "Ready. Next: put your keys in .env, then run"
echo "    uv run python scripts/check.py"
