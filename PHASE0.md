# Phase 0 — setup, before session 1

About 25 minutes. **Do all of it at home.** Session 1 is hands-on from the first
minute and there is no time to install anything in the room.

At the end you run one command and paste one line into a form. That line tells
the instructor whether you're ready, three days early, while there is still time
to fix things by email.

Everything here is free. No credit card is required at any point.

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

## Optional: OpenAI and Anthropic

Notebook 01 compares three providers. It ships with the outputs already saved,
so you can read the comparison without running it, and **you do not need these
keys**.

If you want to run it yourself, both require a payment method and a small
top-up (around €5 each). Add the keys to `.env` and everything else works
unchanged.
