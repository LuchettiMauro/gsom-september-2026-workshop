# Two guards on the Telegram webhook, not one

A tunnel puts a student's agent on the public internet. Two independent checks
now stand in front of it: `TELEGRAM_WEBHOOK_SECRET_TOKEN`, which Agno verifies
and which answers *did Telegram send this*, and `TELEGRAM_ALLOWED_CHAT_IDS`,
which we verify and which answers *is this my conversation*. Neither covers the
other's question.

The secret token is not a hardening option: Agno 2.8.7 rejects every unsigned
update with 403, so a bot without one starts, looks healthy and answers nobody.
`telegram_bot.py` refuses to start rather than reproduce that silent failure.

## Why the allowlist exists

The security argument is real but secondary. Bot usernames are searchable
inside Telegram, and the primary cost of a stranger finding one is not the
Gemini quota — it is that the conversations students collect between the two
sessions *are* the dataset session 2 analyses. A polluted trace set means a
student analysing failures that are not theirs.

## Consequences

Agno exposes no chat filter and no hook to add one, so the allowlist is a
FastAPI middleware in `telegram_bot.py` that inspects the update before the
router sees it. It sits in front of the agent rather than inside it because
answering costs a model call. Do not remove it expecting Agno to cover this.

An unknown chat is logged with its id, which is also how a student discovers
their own: message the bot once, read the number off the console.
