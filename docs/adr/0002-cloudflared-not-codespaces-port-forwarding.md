# The tunnel stays cloudflared, even inside a Codespace

A Codespace can forward a port and hand out a public URL, which would make
`cloudflared` redundant on the recommended route. We install `cloudflared` in
the devcontainer instead and everyone runs the same command, because the
alternative splits the most content-dense part of session 2 into two versions
that must be kept in step.

Notebook 07 is not plumbing: it has a *Why a tunnel* section with a diagram of
the inverted connection direction and three documented failure modes. Port
forwarding would mean rewriting all of it, and would trade three failure modes
that are already written down for a new undocumented one — a forwarded port is
private by default, so Telegram silently gets nothing until someone flips it to
public.

## Consequences

Nobody on this course is ever told to make a forwarded port public. That
matters more than it looks: marimo executes arbitrary Python, so the same
gesture applied to the marimo port hands a stranger a shell in the container.
The devcontainer pins both ports to `private` and says so in a comment.
