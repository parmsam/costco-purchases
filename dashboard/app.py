"""FastHTML app entrypoint."""

import os
import uuid

from fasthtml.common import Beforeware, RedirectResponse, fast_app, serve
from fh_plotly import plotly_headers

from dashboard.data import store
from dashboard.data.store import load_all
from dashboard.layout import theme_headers
from dashboard.routes.departments import register_departments_routes
from dashboard.routes.items import register_items_routes
from dashboard.routes.overview import register_overview_routes
from dashboard.routes.payments import register_payments_routes
from dashboard.routes.receipt import register_receipt_routes
from dashboard.routes.trends import register_trends_routes
from dashboard.routes.upload import register_upload_routes
from dashboard.routes.warehouses import register_warehouses_routes


async def _assign_session(session):
    """Stamp a random id into the (already-existing) signed session cookie.

    On the ephemeral Vercel backend this id is what scopes a visitor's
    in-memory data to them and nobody else; on the local disk backend
    store.set_session_id is a no-op, so this runs unconditionally rather
    than branching on EPHEMERAL here too.

    Must stay async: store.set_session_id writes to a contextvar, and a
    *sync* Beforeware gets dispatched through run_in_threadpool, which
    copies the request's context into a worker thread - a set() made in
    that copy never propagates back out, so the route handler (dispatched
    via its own separate run_in_threadpool call) would still see it unset.
    Staying async runs this in-place in the request's actual task context,
    so the mutation is visible to everything dispatched after it.
    """
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    store.set_session_id(session["sid"])


assign_session = Beforeware(_assign_session)

# Vercel's filesystem is read-only outside /tmp, so the default .sesskey
# file-based secret (written on first run) would crash on cold start there.
# Sessions on that deployment are meant to be throwaway anyway, so a fresh
# random secret per cold start is fine - it just means a visitor's cookie
# stops matching (and they silently get a new empty session) if their
# instance recycles. Locally, secret_key stays None and fast_app falls back
# to its usual .sesskey file, unchanged from before.
_secret_key = uuid.uuid4().hex if os.environ.get("VERCEL") else None

# pico=False: FastHTML bundles Pico.css by default. Pico is classless (styles
# bare <table>/<h1>-<h6>/etc. directly) and switches itself between light and
# dark purely via the OS's prefers-color-scheme — independent of this app's
# own theme toggle. That's what caused tables and page headings to render
# dark/washed-out even while the rest of the page correctly followed the
# app's theme. Nothing here relies on Pico's classless styling (everything
# is MonsterUI components or explicit Tailwind classes), so disabling it
# removes the conflict at the source instead of overriding it element by
# element.
app, rt = fast_app(
    hdrs=(*theme_headers, *plotly_headers),
    pico=False,
    before=assign_session,
    secret_key=_secret_key,
)


@rt("/")
def index():
    receipts_df, _, _ = load_all()
    if receipts_df.empty:
        return RedirectResponse("/upload", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


register_upload_routes(rt)
register_overview_routes(rt)
register_trends_routes(rt)
register_items_routes(rt)
register_warehouses_routes(rt)
register_departments_routes(rt)
register_payments_routes(rt)
register_receipt_routes(rt)


if __name__ == "__main__":
    serve(appname="dashboard.app", port=5001)
