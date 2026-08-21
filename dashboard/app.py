"""FastHTML app entrypoint."""

from fasthtml.common import fast_app, RedirectResponse, serve
from fh_plotly import plotly_headers

from dashboard.data.store import load_all
from dashboard.layout import theme_headers
from dashboard.routes.upload import register_upload_routes
from dashboard.routes.overview import register_overview_routes
from dashboard.routes.trends import register_trends_routes
from dashboard.routes.items import register_items_routes
from dashboard.routes.warehouses import register_warehouses_routes
from dashboard.routes.departments import register_departments_routes
from dashboard.routes.payments import register_payments_routes
from dashboard.routes.receipt import register_receipt_routes


# pico=False: FastHTML bundles Pico.css by default. Pico is classless (styles
# bare <table>/<h1>-<h6>/etc. directly) and switches itself between light and
# dark purely via the OS's prefers-color-scheme — independent of this app's
# own theme toggle. That's what caused tables and page headings to render
# dark/washed-out even while the rest of the page correctly followed the
# app's theme. Nothing here relies on Pico's classless styling (everything
# is MonsterUI components or explicit Tailwind classes), so disabling it
# removes the conflict at the source instead of overriding it element by
# element.
app, rt = fast_app(hdrs=(*theme_headers, *plotly_headers), pico=False)


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
