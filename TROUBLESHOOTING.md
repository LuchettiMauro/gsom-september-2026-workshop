# Troubleshooting

The failures that actually happen, roughly in the order they happen.

---

### "Which terminal am I supposed to type this in?"

The one in your Codespace: the panel along the bottom of the editor, opened
with the **☰** button at the top left, then **View → Terminal**.
[PHASE0.md](PHASE0.md#open-your-codespace) has it with a screenshot. Every
terminal there starts at the repository root, the folder holding
`pyproject.toml`, which is where the commands assume you are.

Two rules that account for most of the confusion:

- Commands starting with `uv`, `git`, `cd` or `curl` go to a **shell**. Typing
  them into a notebook cell gives you `SyntaxError: invalid syntax`.
- The terminal running `uv run marimo edit` is **occupied** for as long as
  marimo runs. Anything else needs a second terminal window or tab.

---

### How do I open a second terminal?

Three routes to the same thing, all in the Codespace window:

- the **+** button at the top right of the panel holding the **TERMINAL** tab —
  the terminals you have open are listed on the right, click a row to switch;
- `` Ctrl+Shift+` ``;
- the **☰** button at the top left, then **Terminal → New Terminal**.

The icon next to the **+** is *Split Terminal*, which puts two side by side in
one panel instead of switching between them — handy in session 2, where you
want to watch the bot and the tunnel at once.

Each one starts at the repository root, so there is nothing to `cd` to.

---

### I restarted the Codespace and I'm not in `.venv` any more

You do not need to be. Every command in this workshop starts with `uv run`,
which locates the project's environment itself — `uv run marimo edit
--no-token`, `uv run python scripts/check.py`, `uv run pytest`. There is
nothing to activate and nothing to `source`, and the `(polimi-workshop)` prefix
on the prompt is not a requirement for any of it.

What a restart really costs you is the *running* processes. marimo is not
serving any more, so start it again:

```
uv run marimo edit --no-token
```

Same for session 2: the bot and the tunnel are both gone, and the tunnel hands
out a new address each time, so notebook 07's webhook has to be pointed at the
new one.

---

### marimo asks for an access key, or I can't tell what to click to open it

Start it as the guide does, with the flag:

```
uv run marimo edit --no-token
```

marimo's default is to guard the server with an access key that travels in the
URL it prints. The tab a Codespace opens for you is `localhost:2718` without
that query string, so you meet a login box and the only copy of the key is in
the terminal. `--no-token` removes the box. The server is still reachable only
through your private forwarded port.

If you have already started it without the flag, either stop it with `Ctrl+C`
and start it again, or copy the whole URL from the terminal — the part after
`?access_token=` is the key it is asking for.

To open it: click **Open in Browser** in the notification at the bottom right,
or use the **PORTS** tab beside TERMINAL and click the globe icon on the
*marimo* row.

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

Your branch does not hold the whole package. Branching from `main` in Phase 0
gives you every module the notebooks use; branching from a `step-*` checkpoint
gives you only the modules that existed at that point in the course.

Check where you are:

```
git branch --show-current
ls stargate
```

If the module is missing, move onto your own branch off `main`:

```
git add -A && git commit -m "my work so far"
git fetch origin
git switch -c mywork origin/main
```

Then **shut the notebook down and open it again** from marimo's home page. A
running kernel has already decided that `stargate.tools` does not exist and
will keep saying so, however many times you re-run the cell.

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

### `uv: command not found`

`uv` is baked into the Codespace image, so this means the image did not finish
building. Rebuild the container: `F1`, then **Codespaces: Rebuild Container**.
If that does not fix it, delete the codespace from
[github.com/codespaces](https://github.com/codespaces) and create a new one —
you lose only `.env`, which is four lines of pasting.

---

### `GOOGLE_API_KEY is not set`

Three possibilities, in order of likelihood:

1. You edited `.env.example` instead of `.env`. The two sit next to each other
   in the file list and only `.env` is read.
2. You did not save the file. `Ctrl+S`, or `Cmd+S` on a Mac.
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

### `503` / `UNAVAILABLE` / "this model is currently experiencing high demand"

Not your key, and nothing you did: Google's free tier is loaded and is turning
requests away. It clears on its own, usually within minutes.

`scripts/check.py` already retries twice before reporting it. If it still
fails, wait a few minutes and run it again — and if you are checking the
evening before a session, remember that the rest of the room is doing the same
thing at the same time.

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
