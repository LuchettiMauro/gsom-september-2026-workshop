import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 07 · The agent, on your phone

    **Start here.** This notebook needs `telegram_bot.py`, which arrives on
    `step-07`. Run this in a terminal, in the repository root — not in a cell
    of this notebook, and not in the terminal marimo is running in:

    ```
    git add -A && git commit -m "my work so far"
    git fetch origin
    git switch -c mywork-07 origin/step-07
    ```

    Then shut this notebook down from marimo's home page and open it again, so
    the kernel picks up the files that just appeared.

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
        print("TELEGRAM_TOKEN is not set — see PHASE0.md step 6.")
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
        _result = httpx.post(
            f"https://api.telegram.org/bot{cfg.telegram_token}/setWebhook",
            json={"url": f"{TUNNEL_URL}/telegram/webhook"},
            timeout=30,
        ).json()
        print(_result)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Now open Telegram on your phone, find your bot, and ask it something.

    Watch terminal 1. Watch Langfuse.

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

    **That URL is unauthenticated.** Anyone who learns it can drive your agent and
    spend your quota. Random subdomains make that unlikely, not impossible. The
    real fix is `TELEGRAM_WEBHOOK_SECRET_TOKEN`, which makes Telegram sign every
    request with a header you verify — two lines, and the difference between a
    demo and something you would leave running.

    **You have now made an LLM application available to the public.** If you were
    doing this for real, in the EU, Google's API terms would matter: *"You may use
    only Paid Services when making API Clients available to users in the European
    Economic Area, Switzerland, or the United Kingdom."* Free tier is for
    development. This is development. Shipping it would not be.

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
