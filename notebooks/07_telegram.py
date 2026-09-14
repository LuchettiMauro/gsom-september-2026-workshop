import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 07 · The agent, on your phone

    **This notebook uses `telegram_bot.py`.** It is already in your
    repository: nothing to fetch, nothing to switch.

    If an import fails, you are sitting on a `step-*` branch rather than your
    own — see *cannot import name* in TROUBLESHOOTING.md.

    ---

    Everything so far has run inside a notebook. That is fine for exploring and
    useless for anything else.

    This notebook is different in kind: it *orchestrates* a running process rather
    than containing one. A Telegram bot is an HTTP server, and a notebook cell
    that blocks forever is a notebook you have lost.

    You will need three terminals. That is not a workaround — it is what
    deploying this actually looks like.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Why a tunnel

    Telegram's model is **inbound**: when someone messages your bot, Telegram's
    servers make an HTTPS POST to a URL you registered.

    Your laptop has no public IP, no DNS name, and no TLS certificate. Telegram
    refuses plain HTTP and refuses invalid certificates. So there is no way for it
    to reach `localhost:7777`.

    A tunnel inverts the direction:

    ```
    your laptop  ──outbound──>  cloudflare edge  <──inbound──  Telegram
                 (you open it)   (public HTTPS)     (POSTs here)
    ```

    `cloudflared` opens a connection *out* from your machine and holds it. Requests
    arriving at the public hostname are pushed back down the connection you already
    opened. Firewalls and NAT only block unsolicited *inbound* traffic, so this
    works from a lecture room, a train, or behind a corporate proxy.

    No port forwarding, no router configuration, no account.
    """)
    return


@app.cell
def _():
    from stargate.config import settings

    cfg = settings()
    if cfg.telegram_token:
        print(f"Telegram token: ...{cfg.telegram_token[-6:]}")
    else:
        print("TELEGRAM_TOKEN is not set — see PHASE0.md, *Get a Telegram bot token*.")
    return (cfg,)


@app.cell
def _(cfg):
    import httpx

    _me = httpx.get(f"https://api.telegram.org/bot{cfg.telegram_token}/getMe", timeout=20).json()
    print(_me["result"]["username"] if _me.get("ok") else _me)
    return (httpx,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Before terminal 1 — two locks on the door

    A tunnel puts your agent on the public internet, so `telegram_bot.py`
    checks two things in `.env` before it will serve anything.

    `TELEGRAM_WEBHOOK_SECRET_TOKEN` is a string Telegram sends back in a header
    on every delivery, proving the request is really theirs. Agno verifies it
    and **rejects anything unsigned with a 403** — so this is not a hardening
    step you can skip, it is the difference between a bot that answers and a
    bot that silently answers nobody.

    `TELEGRAM_ALLOWED_CHAT_IDS` is the list of chats the agent will reply to.
    Bot usernames are searchable inside Telegram: without this, a stranger can
    find yours, spend your Gemini quota, and land in the traces you are
    collecting for session 2. You fill it in a few cells from here.

    Run the cell below, then put the line it prints into `.env`.
    """)
    return


@app.cell
def _(cfg):
    import secrets

    if cfg.telegram_webhook_secret:
        print("TELEGRAM_WEBHOOK_SECRET_TOKEN is set — nothing to do.")
    else:
        print("Add this line to .env, then restart this notebook's kernel:\n")
        print(f"TELEGRAM_WEBHOOK_SECRET_TOKEN={secrets.token_urlsafe(32)}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Terminal 1 — the bot

    ```bash
    uv run python telegram_bot.py
    ```

    Open `telegram_bot.py` in your editor while it starts. It is about thirty
    lines: build the agent you already have, wrap it in `AgentOS`, attach the
    Telegram interface, serve it.

    ## Terminal 2 — the tunnel

    ```bash
    cloudflared tunnel --url http://localhost:7777
    ```

    It prints a URL like `https://something-random-here.trycloudflare.com`.

    **That URL changes every time you restart the tunnel**, which is the single
    most common thing to get wrong in this notebook. Copy it into the cell below.
    """)
    return


@app.cell
def _():
    # Paste the URL cloudflared printed. No trailing slash.
    TUNNEL_URL = "https://REPLACE-ME.trycloudflare.com"
    return (TUNNEL_URL,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Terminal 3 — this notebook: register the webhook

    One call. This is what tells Telegram where to deliver messages.
    """)
    return


@app.cell
def _(TUNNEL_URL, cfg, httpx):
    if "REPLACE-ME" in TUNNEL_URL:
        print("Paste your cloudflared URL into the cell above first.")
    else:
        # secret_token is what Telegram echoes back in the
        # X-Telegram-Bot-Api-Secret-Token header on every delivery.
        _result = httpx.post(
            f"https://api.telegram.org/bot{cfg.telegram_token}/setWebhook",
            json={
                "url": f"{TUNNEL_URL}/telegram/webhook",
                "secret_token": cfg.telegram_webhook_secret,
            },
            timeout=30,
        ).json()
        print(_result)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Now open Telegram on your phone, find your bot, and ask it something.

    Watch terminal 1. Watch Langfuse.

    ## Close the door behind you

    Your first message will be *ignored*, and terminal 1 will print something
    like:

    ```
    ignored a message from chat 123456789 — add it to TELEGRAM_ALLOWED_CHAT_IDS in .env if it is yours
    ```

    That number is your chat id. Put it in `.env`:

    ```
    TELEGRAM_ALLOWED_CHAT_IDS=123456789
    ```

    Restart terminal 1 and ask again. Now it answers you, and only you.

    ## If nothing happens

    `getWebhookInfo` tells you what Telegram thinks, including the last error it
    got when it tried to deliver.
    """)
    return


@app.cell
def _(cfg, httpx):
    _info = httpx.get(
        f"https://api.telegram.org/bot{cfg.telegram_token}/getWebhookInfo", timeout=20
    ).json()
    for _k, _v in _info.get("result", {}).items():
        print(f"{_k}: {_v}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Common causes, in order:

    1. You restarted the tunnel and did not re-register. The URL changed.
    2. The URL is missing `/telegram/webhook`.
    3. Your network blocks outbound tunnels. Tether to your phone.

    ## Two things worth saying out loud

    **A random URL is not a lock.** Anyone who learns your tunnel address can
    POST to it, and `trycloudflare` subdomains do get scanned. That is why the
    two guards are separate: the secret token answers *did Telegram send this*,
    and the allowlist answers *is this my conversation*. Neither covers the
    other's question, which is the general shape of the thing — authentication
    and authorisation are different locks.

    **You have now made an LLM application available to the public.** If you were
    doing this for real, in the EU, Google's API terms would matter: *"You may use
    only Paid Services when making API Clients available to users in the European
    Economic Area, Switzerland, or the United Kingdom."* Free tier is for
    development. This is development. Shipping it would not be.

    ---
    """)
    return


@app.cell
def _(cfg, httpx):
    # Run this when you are done for the day.
    _gone = httpx.post(
        f"https://api.telegram.org/bot{cfg.telegram_token}/deleteWebhook", timeout=20
    ).json()
    print(_gone)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Shutting it down

    A registered webhook outlives the tunnel it points at. Leave one behind and
    Telegram keeps trying to deliver to an address that belongs to nobody, and
    your next session opens with a bot that looks broken. So when you are done,
    in this order:

    1. run the `deleteWebhook` cell above,
    2. `Ctrl+C` the tunnel in terminal 2,
    3. `Ctrl+C` the bot in terminal 1,
    4. and on Codespaces, stop the container — it bills you for staying awake,
       not for the work it does.

    ## The version you will actually use

    You have now seen the three pieces separately, which was the point. For the
    days between the two sessions, one command does all of it: generates the
    secret, waits for the bot, reads the tunnel URL, registers the webhook, and
    deletes it again on `Ctrl+C`.

    ```bash
    uv run python scripts/serve_bot.py
    ```

    Read it before you trust it. `scripts/serve_bot.py` is about a hundred
    lines and does nothing this notebook has not already done by hand.

    ---

    ### Checkpoint

    Reference state: **`step-07`**

    Next: `notebooks/08_evals.py` — the part that matters.

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit notebooks/08_evals.py`.

    See *Running the notebooks* in the README if this is the first time.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
