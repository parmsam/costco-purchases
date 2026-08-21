"""GET /dashboard — KPI cards + monthly trend + recent receipts."""

import plotly.express as px

from monsterui.franken import A

from dashboard.analytics.filters import load_filtered
from dashboard.analytics.kpis import compute_kpis
from dashboard.analytics.trends import monthly_spend
from dashboard.charts import chart_card
from dashboard.components import empty_state, kpi_card, kpi_row, section, sortable_table
from dashboard.data.store import get_upload_history
from dashboard.layout import page
from dashboard.palette import SINGLE_SERIES


def register_overview_routes(rt):
    @rt("/dashboard")
    def get(start: str = "", end: str = ""):
        receipts_df, items_df, _, filter_bar = load_filtered("/dashboard", start, end)

        if filter_bar is None:
            return page(
                "Dashboard",
                empty_state("No purchase history yet. Import a JSON or CSV export to get started."),
                active="/dashboard",
            )

        if receipts_df.empty:
            return page(
                "Dashboard",
                section("No receipts in this range", "Try widening the date filter above."),
                active="/dashboard",
                filter_bar=filter_bar,
            )

        history = get_upload_history()
        subtitle = f"Last imported {history[0]['timestamp'][:10]} — {history[0]['filename']}" if history else ""

        k = compute_kpis(receipts_df, items_df)
        cards = kpi_row(
            kpi_card("Total Spend", f"${k['total_spend']:,.2f}", icon="dollar-sign"),
            kpi_card("Receipts", f"{k['receipt_count']:,}", icon="receipt"),
            kpi_card("Date Range", k["date_range"], icon="calendar-range"),
            kpi_card("Avg Basket", f"${k['avg_basket']:,.2f}", icon="shopping-basket"),
            kpi_card(
                "Instant Savings",
                f"${k['total_instant_savings']:,.2f}",
                sub=f"${k['instant_savings_line_items']:,.2f} from item-level lines",
                icon="badge-percent",
            ),
            kpi_card("Avg Items/Receipt", f"{k['avg_items_per_receipt']:.1f}", icon="package"),
        )

        trend_df = monthly_spend(receipts_df)
        fig = px.bar(trend_df, x="month", y="total", labels={"month": "Month", "total": "Spend ($)"})
        fig.update_traces(marker_color=SINGLE_SERIES, marker_line_width=0)
        trend_chart = chart_card(fig)

        recent = receipts_df.sort_values("transaction_date", ascending=False).head(10)
        recent_table = sortable_table(
            header_data=["Date", "Warehouse", "Total"],
            body_data=[
                {
                    "Date": A(
                        f"{row.transaction_date:%Y-%m-%d}" if row.transaction_date is not None else "",
                        href=f"/receipt/{row.receipt_id}",
                        cls="text-primary hover:underline",
                    ),
                    "Warehouse": row.warehouse_name,
                    "Total": f"${row.total:,.2f}",
                }
                for row in recent.itertuples()
            ],
        )

        return page(
            "Dashboard",
            cards,
            section("Monthly Spend", trend_chart, icon="bar-chart-3"),
            section("Recent Receipts", recent_table, icon="clock"),
            active="/dashboard",
            subtitle=subtitle,
            filter_bar=filter_bar,
        )
