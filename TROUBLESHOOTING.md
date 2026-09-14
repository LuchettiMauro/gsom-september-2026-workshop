# Troubleshooting

The failures that actually happen, roughly in the order they happen.

---

### "Which terminal am I supposed to type this in?"

Any of them — your OS terminal or your editor's built-in one — as long as the
working directory is the repository root, the folder holding `pyproject.toml`.
[PHASE0.md](PHASE0.md) walks through opening one, on a Codespace and on
each platform.

Two rules that account for most of the confusion:

- Commands starting with `uv`, `git`, `cd` or `curl` go to a **shell**. Typing
  them into a notebook cell gives you `SyntaxError: invalid syntax`.
- The terminal running `uv run marimo edit` is **occupied** for as long as
  marimo runs. Anything else needs a second terminal window or tab.

---

### The terminal ignores what I type / it just prints marimo log lines

That is the terminal marimo is running in, and it stays that way until marimo
stops. Open a second one and work there.

If you actually want to stop marimo: `Ctrl+C` in that terminal. That shuts down
the *server* and every notebook it was serving.

---

### I finished a notebook. How do I close it and open the next one?

On marimo's home page (the browser tab at the server URL): find the notebook
under **Running notebooks**, click the round **Shutdown** button on its row,
confirm, then click the next notebook in the list.

If you started marimo on a single file (`uv run marimo edit notebooks/05_...`),
there is no home page — press `Ctrl+C` in that terminal and start the next one.

Closing the browser tab does **not** close the notebook. The kernel keeps
running, holding its memory and its clients, until you shut it down or stop the
server. Leaving several running is a common cause of the machine getting slow
halfway through a session.

---

### I switched branches and the notebook still shows the old code

The file on disk changed underneath a running kernel. Shut that notebook down
from marimo's home page and open it again. Do the `git switch` *before*
opening the notebook, not while it is running.

---

### `cannot import name 'tools' from 'stargate'` (or `agents`, `knowledge`, `teams`, `loop`…)

The module is not on your branch yet. Each notebook reads code that arrives with
its own `step-NN` branch, and the **Start here** block at the top of the notebook
is what puts it there. Run it:

```
git add -A && git commit -m "my work so far"
git fetch origin
git switch -c mywork-02 origin/step-02
```

(with the branch that notebook names — `02_tool_calling` wants `step-02`,
`05_knowledge` wants `step-05`, and so on).

Then **shut the notebook down and open it again**. A running kernel has already
decided that `stargate.tools` does not exist and will keep saying so, however
many times you re-run the cell.

Confirm with `git branch --show-current` and `ls stargate` — the module should be
sitting there.

---

### `No module named 'sqlalchemy'` (or another package the notebook clearly needs)

Your environment was installed before that dependency was added to
`pyproject.toml`. Pull and re-sync:

```
git pull
uv sync --extra serve
```

Then restart the notebook — a running kernel keeps the old environment.

If the missing package is `telebot`, `fastapi` or `uvicorn`, it is the
`--extra serve` that is missing rather than the sync: those three only install
with it, and `uv run python scripts/check.py` reports them as `serve=MISSING`.

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

You skipped `fetch_data.py`:

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

Run the `getWebhookInfo` cell in notebook 07: `last_error_message` says which
of these it is.

---

### The bot is running, the tunnel is up, and every message is silently ignored

Two guards can drop a message, and they fail differently.

**`403` in `getWebhookInfo`, or `Invalid webhook secret token` in terminal 1.**
Telegram is delivering, and Agno is refusing. The `secret_token` you registered
with `setWebhook` does not match `TELEGRAM_WEBHOOK_SECRET_TOKEN` in `.env` —
usually because you changed one and not the other. Re-run the `setWebhook`
cell, which reads the current value.

**`ignored a message from chat 123456789` in terminal 1.** That is our
allowlist, not Agno. The chat you are writing from is not in
`TELEGRAM_ALLOWED_CHAT_IDS`. Copy the number from that line into `.env` and
restart the bot: a running process keeps the old settings.

**Nothing at all in terminal 1.** Telegram is not reaching you. That is the
previous entry, not this one.

---

### The agent gives an answer that is simply wrong

Good. Write down what was wrong, in one sentence, in your own words.

That's the homework, and it's the raw material for session 2. Don't fix it.
