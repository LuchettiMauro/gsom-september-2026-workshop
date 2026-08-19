# Phase 0 — setup, before session 1

About 25 minutes. **Do all of it at home.** Session 1 is hands-on from the first
minute and there is no time to install anything in the room.

At the end you run one command and paste one line into a form. That line tells
the instructor whether you're ready, three days early, while there is still time
to fix things by email.

Everything here is free. No credit card is required at any point.

---

## 0. Open a terminal

Every command in this workshop is typed into a terminal. Which one does not
matter much, but you have to know where it is, so pick one now and use the same
one throughout.

**Windows** — use **PowerShell**, not the old `cmd` prompt. Press `Win`, type
`powershell`, press Enter. If you have Windows Terminal installed, that opens
PowerShell by default and is nicer. Some commands below differ between
PowerShell and `cmd`; where they do, this guide says which is which.

**macOS** — press `Cmd+Space`, type `terminal`, press Enter. iTerm2 works
identically if you already have it.

**Linux** — whatever your distribution gave you: `Ctrl+Alt+T` opens it on most.

**Or your editor's built-in terminal.** VS Code, PyCharm and Cursor all have
one, and it is the more comfortable option because the terminal and the files
are in the same window:

- **VS Code / Cursor**: `File → Open Folder` on the cloned repo, then
  `` Ctrl+` `` (`` Cmd+` `` on macOS), or `View → Terminal`.
- **PyCharm**: `Alt+F12`, or `View → Tool Windows → Terminal`.

The built-in terminal is the *same* shell as the OS one — on Windows check the
dropdown in the terminal panel says `powershell` and not `Command Prompt`.

Three things that matter regardless of which you picked:

1. **Your working directory must be the repository root.** That is the folder
   containing `pyproject.toml`. Every command in this guide assumes it. After
   step 3 you get there with `cd polimi-workshop`; check with `pwd` (macOS,
   Linux, PowerShell) or `cd` with no arguments (Windows `cmd`).
2. **"Close and reopen your terminal" means the whole window**, not just a new
   tab in the same one. Installers change `PATH`, and only a freshly started
   shell reads it. In VS Code that means closing the terminal panel with the
   bin icon and opening a new one — or, if that still fails, restarting the
   editor.
3. **You will need a second terminal in session 2**, running alongside the
   first — one for the tunnel, one for the bot. Open a second window, or a
   second tab (`Ctrl+Shift+5` in VS Code splits the panel). Both need to be in
   the repository root.

> **Do not use a Python REPL or a Jupyter cell for these.** Commands starting
> with `uv`, `git`, `cd` or `curl` go to the shell. If you see
> `SyntaxError: invalid syntax` on a line starting with `uv`, you typed a shell
> command into Python.

---

## 1. Install `uv`

`uv` manages both Python and the project's dependencies, so you do **not** need
to install Python yourself — whatever version you already have is irrelevant.

**Windows** (PowerShell):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen your terminal, then check:
```
uv --version
```

## 2. Install `cloudflared`

Needed in session 2, to give your agent a public address. Installing it now
means one less thing to go wrong later.

**Windows**: `winget install --id Cloudflare.cloudflared`
**macOS**: `brew install cloudflared`
**Linux**: see https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

Then close and reopen your terminal, as in step 1: the installer adds
`cloudflared` to `PATH`, and a terminal that was already open keeps the old one.
Check with `cloudflared --version`.

## 3. Get the code

```bash
git clone https://github.com/<org>/polimi-workshop.git
cd polimi-workshop
git switch -c mywork origin/step-00
uv sync
```

The `git switch -c mywork` matters: it puts you on your own branch from the
start. The `step-*` branches are regenerated between sessions, and anything you
commit directly onto one will be overwritten.

## 4. Get a Google AI Studio key

1. Go to https://aistudio.google.com/apikey
2. Sign in with any Google account
3. **Create API key**, then copy it

Free, and no credit card. This is the only key you actually need.

> If you're in the EU, your prompts on the free tier get the same data
> protections as the paid tier. Google's terms make that explicit for the EEA,
> Switzerland and the UK.

## 5. Get a Langfuse account

This is where every agent run gets recorded. You'll spend half of session 2
looking at your own traces here.

1. Go to https://cloud.langfuse.com and sign up
2. **Choose the EU region** when asked
3. Create an organisation, then a project (call it anything)
4. Settings → API Keys → **Create new API key**
5. Copy both the public key (`pk-lf-...`) and the secret key (`sk-lf-...`)

## 6. Get a Telegram bot token

Used in session 2. Takes about 30 seconds and the token never expires.

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Pick a name, then a username ending in `bot`
4. Copy the token it gives you

## 7. Fill in your keys

```bash
cp .env.example .env        # macOS / Linux
copy .env.example .env      # Windows cmd
Copy-Item .env.example .env # Windows PowerShell
```

Open `.env` and paste in the four values from steps 4–6. `.env` is git-ignored,
so your keys never leave your machine.

## 8. Download the data

```bash
uv run python scripts/fetch_data.py
```

Fetches 42 declassified documents and ~60,000 UFO sighting reports. About a
minute.

## 9. Run the check

```bash
uv run python scripts/check.py
```

This makes a real (tiny) call to Gemini, writes a real trace to Langfuse, and
downloads the local embedding model — roughly 80 MB, which is exactly the sort
of thing that should not happen 25 times over lecture-room wifi.

It prints something like:

```
READY  uv=0.9.2  python=3.12.8  gemini=ok  langfuse=ok  telegram=ok
       fastembed=ok  cloudflared=ok  marimo=ok  data=ok
```

## 10. Submit that line

Paste the `READY ...` line into the form linked in the course announcement, at
least **three days before session 1**.

If anything says `MISSING` or `FAILED`, check
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) first — and if it's still broken, send
the output. That's what the three days are for.

---

## 11. Optional: open the first notebook once

Not required, but it removes the last surprise from the start of session 1.

```bash
uv run marimo edit
```

Your browser opens on marimo's home page, listing every notebook in the
repository. Click `notebooks/01_chat_completions.py`. You do not need to run
anything — just confirm it opens.

To stop: `Ctrl+C` in that terminal. The full workflow, including how to close
one notebook and open the next, is in *Running the notebooks* in
[README.md](README.md#running-the-notebooks).

---

## Optional: OpenAI and Anthropic

Notebook 01 compares three providers. It ships with the outputs already saved,
so you can read the comparison without running it, and **you do not need these
keys**.

If you want to run it yourself, both require a payment method and a small
top-up (around €5 each). Add the keys to `.env` and everything else works
unchanged.
