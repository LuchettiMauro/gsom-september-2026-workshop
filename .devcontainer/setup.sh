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
uv run python scripts/fetch_data.py

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
