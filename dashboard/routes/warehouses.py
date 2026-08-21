"""GET /warehouses — spend by warehouse (chart + table)."""

import plotly.express as px

from dashboard.analytics.filters import load_filtered
from dashboard.analytics.warehouses import spend_by_warehouse
from dashboard.charts import chart_card
from dashboard.components import empty_state, section, sortable_table
from dashboard.layout import page
from dashboard.palette import SINGLE_SERIES


def register_warehouses_routes(rt):
    @rt("/warehouses")
    def get(start: str = "", end: str = ""):
        receipts_df, _, _, filter_bar = load_filtered("/warehouses", start, end)

        if filter_bar is None:
            return page(
                "Warehouses",
                empty_state("No purchase history yet. Import a JSON or CSV export to get started."),
                active="/warehouses",
            )

        if receipts_df.empty:
            return page(
                "Warehouses",
                section("No receipts in this range", "Try widening the date filter above."),
                active="/warehouses",
                filter_bar=filter_bar,
            )

        by_wh = spend_by_warehouse(receipts_df)
        fig = px.bar(
            by_wh.sort_values("total_spend"),
            x="total_spend",
            y="warehouse_name",
            orientation="h",
            labels={"warehouse_name": "", "total_spend": "Spend ($)"},
        )
        fig.update_traces(marker_color=SINGLE_SERIES, marker_line_width=0)
        chart = chart_card(fig, height=max(240, 60 * len(by_wh)))

        table = sortable_table(
            header_data=["Warehouse", "Spend", "Visits", "Avg Basket"],
            body_data=[
                {
                    "Warehouse": row.warehouse_name,
                    "Spend": f"${row.total_spend:,.2f}",
                    "Visits": row.visits,
                    "Avg Basket": f"${row.avg_basket:,.2f}",
                }
                for row in by_wh.itertuples()
            ],
        )

        return page(
            "Warehouses",
            section("Spend by Warehouse", chart, icon="bar-chart-3"),
            section("Details", table, icon="table"),
            active="/warehouses",
            subtitle="Where you shop",
            filter_bar=filter_bar,
        )
