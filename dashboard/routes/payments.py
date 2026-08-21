"""GET /payments — payment-method breakdown; empty-state message when tenders_df is empty (CSV-only import)."""

import plotly.express as px

from dashboard.analytics.filters import load_filtered
from dashboard.analytics.payments import (
    monthly_spend_by_method,
    payment_kpis,
    payment_method_details,
    spend_by_payment_method,
)
from dashboard.charts import chart_card
from dashboard.components import empty_state, kpi_card, kpi_row, section, sortable_table
from dashboard.layout import page
from dashboard.palette import CATEGORICAL


def register_payments_routes(rt):
    @rt("/payments")
    def get(start: str = "", end: str = ""):
        receipts_df, _, tenders_df, filter_bar = load_filtered("/payments", start, end)

        if filter_bar is None:
            return page(
                "Payments",
                empty_state("No purchase history yet. Import a JSON or CSV export to get started."),
                active="/payments",
            )

        if receipts_df.empty:
            return page(
                "Payments",
                section("No receipts in this range", "Try widening the date filter above."),
                active="/payments",
                filter_bar=filter_bar,
            )

        if tenders_df.empty:
            return page(
                "Payments",
                empty_state(
                    "No payment-method data available. This appears when your purchase history "
                    "was imported from CSV, which doesn't include payment tenders — re-import "
                    "the JSON export to see this breakdown.",
                    icon="credit-card",
                    cta_label="Re-import JSON",
                ),
                active="/payments",
                filter_bar=filter_bar,
            )

        k = payment_kpis(tenders_df)
        cards = kpi_row(
            kpi_card("Transactions", f"{k['transaction_count']:,}", icon="receipt"),
            kpi_card("Payment Methods", f"{k['method_count']}", icon="wallet"),
            kpi_card(
                "Top Method",
                k["top_method"],
                sub=f"{k['top_method_pct']:.0f}% of spend",
                icon="star",
            ),
            kpi_card("Avg Transaction", f"${k['avg_transaction']:,.2f}", icon="calculator"),
        )

        by_method = spend_by_payment_method(tenders_df)
        fig = px.pie(
            by_method,
            names="tender_type_name",
            values="total",
            hole=0.55,
            color_discrete_sequence=CATEGORICAL,
        )
        fig.update_traces(textinfo="percent+label", textposition="outside")
        chart = chart_card(fig, height=420)

        sections = [
            section("Payment Methods", chart, icon="bar-chart-3"),
        ]

        monthly = monthly_spend_by_method(tenders_df, receipts_df)
        if not monthly.empty and monthly["month"].nunique() > 1:
            trend_fig = px.bar(
                monthly,
                x="month",
                y="total",
                color="tender_type_name",
                labels={"month": "Month", "total": "Spend ($)", "tender_type_name": "Method"},
                color_discrete_sequence=CATEGORICAL,
            )
            trend_fig.update_layout(barmode="stack")
            sections.append(section("Spend by Method Over Time", chart_card(trend_fig), icon="calendar-days"))

        details = payment_method_details(tenders_df)
        details_table = sortable_table(
            header_data=["Method", "Spend", "Transactions", "Avg", "% of Spend"],
            body_data=[
                {
                    "Method": row.tender_type_name,
                    "Spend": f"${row.total:,.2f}",
                    "Transactions": row.count,
                    "Avg": f"${row.avg:,.2f}",
                    "% of Spend": f"{row.pct:.1f}%",
                }
                for row in details.itertuples()
            ],
        )
        sections.append(section("Details", details_table, icon="table"))

        return page(
            "Payments",
            cards,
            *sections,
            active="/payments",
            subtitle="How you pay at checkout",
            filter_bar=filter_bar,
        )
