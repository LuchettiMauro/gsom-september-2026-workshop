# Troubleshooting

The failures that actually happen, roughly in the order they happen.

---

### `uv: command not found` after installing it

The installer adds `uv` to your PATH, but only for *new* terminals. Close the
terminal and open a new one.

On Windows, if PowerShell refuses to run the installer at all, it's the
execution policy — use the exact command from PHASE0.md, which includes
`-ExecutionPolicy ByPass`.

---

### `GOOGLE_API_KEY is not set`

Three possibilities, in order of likelihood:

1. You created `.env.example` instead of `.env`. The file must be called exactly
   `.env`, in the repository root.
2. Windows saved it as `.env.txt`. File Explorer hides extensions by default —
   check with `dir` in the terminal, not in Explorer.
3. There are quotes or spaces around the value. It should read
   `GOOGLE_API_KEY=AIza...` with nothing else on the line.

---

### "This model models/… is no longer available to new users"

Google retires Gemini models on its own schedule. A retired model keeps working
for projects that already used it, so an old key succeeds while a freshly created
one gets this error on the same model name.

Fix it by naming a current model in `.env`:

```
STARGATE_MODEL=gemini-3.1-flash-lite
```

`uv run python scripts/check.py` prints the models your key can actually see when
the configured one is rejected, so you can pick from that list. Prefer a
`flash-lite` model: the workshop's agent loops need the higher requests-per-minute
allowance.

---

### `429` / `RESOURCE_EXHAUSTED` / "rate limited"

You've hit the free-tier limit: about **15 requests per minute** on
`gemini-3.1-flash-lite`, plus a daily cap.

A single agent question costs several model calls, so this arrives sooner than
you'd expect — which is itself worth noticing. The code retries automatically
with increasing delays. If it keeps failing:

- Wait a minute. The per-minute limit resets quickly.
- If you've exhausted the *daily* limit, ask the instructor for the room key.

---

### The notebook re-runs cells I didn't touch, and it costs API calls

marimo is reactive: editing a cell re-runs everything downstream. Since
downstream cells call models, that gets expensive.

The repo ships configured for **lazy** mode, where dependent cells are marked
stale instead of re-running. If yours is re-running eagerly, check the runtime
setting in marimo's configuration panel (top right) and set
"On cell change" to **lazy**.

---

### `This notebook defines the same variable in two cells`

That's marimo's core rule: each global name is defined by exactly one cell. It's
what lets it re-run only what's affected.

Two ways out:

- Prefix with an underscore (`_response`) to make it local to the cell.
- Wrap the working code in a function.

---

### `No sightings data at data/nuforc.parquet`

You skipped step 8:

```bash
uv run python scripts/fetch_data.py
```

---

### `No index at lancedb/`

Notebook 05 builds it. If you're starting from a later notebook:

```python
from stargate.knowledge import restore_prebuilt_index

restore_prebuilt_index()
```

---

### Nothing appears in Langfuse

- Traces are batched. Call `stargate.observability.flush()` — the notebooks do
  this at the end, but if you stopped halfway the last runs may still be queued.
- Check you're looking at the right project, and the right **region**. An EU
  account's traces are not visible on the US dashboard.
- Confirm both keys are in `.env`: the public key alone is not enough.

---

### `cloudflared` starts but Telegram never calls back

- Did you re-register the webhook after restarting the tunnel? The URL changes
  every time. Re-run the `setWebhook` cell.
- Is the tunnel URL `https`? Telegram refuses plain HTTP.
- Some networks block outbound tunnels. Tether to your phone and try again —
  this is the single most likely cause on a university network.

---

### The agent gives an answer that is simply wrong

Good. Write down what was wrong, in one sentence, in your own words.

That's the homework, and it's the raw material for session 2. Don't fix it.
