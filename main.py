"""Vercel entrypoint.

Vercel's Python runtime looks for a top-level `app` in a root-level file
named app.py/main.py/etc. (see https://vercel.com/docs/functions/runtimes/python).
The actual app is defined in dashboard/app.py, which auto-selects the
ephemeral in-memory store over the local disk store because Vercel sets
VERCEL=1 in its runtime - see dashboard/data/store.py.

Not used for local dev; run `python -m dashboard.app` (or the local dev
skill/scripts) for that instead.
"""

from dashboard.app import app  # noqa: F401
