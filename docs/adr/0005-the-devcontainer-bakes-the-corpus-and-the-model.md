# The devcontainer bakes the dependencies, the corpus and the embedding model

`.devcontainer/setup.sh` installs `uv` and `cloudflared`, runs
`uv sync --extra serve`, fetches the 42 documents and the sightings parquet,
and downloads the 80 MB embedding model — all at image build time, with
prebuilds enabled on `main` so a student pays none of it. This is what reduces
Phase 0 to the four API keys.

A lighter image was considered. The argument for it is pedagogical: a student
who never watches `uv sync` run learns a little less about how a Python
project is installed. That is a real loss, and it is why the local route still
does all of this by hand.

## Consequences

`stargate/config.py` sets `FASTEMBED_CACHE_PATH` to `data/.cache`. FastEmbed
otherwise caches into the system temp directory, which does not survive into a
container image, and which Linux cleans out from under a local install too —
either way the 80 MB is silently downloaded again.

A prebuild can bake a failure: if `fetch_data.py`'s source moves, the image
ships without a corpus. `scripts/check.py` already counts the documents and
reports `data=MISSING` with the command to fix it, so this degrades into one
extra command rather than a blocked student.
