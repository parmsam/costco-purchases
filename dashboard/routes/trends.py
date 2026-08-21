"""GET /trends — monthly spend chart, month-over-month table, year-over-year comparison."""

import plotly.express as px

from dashboard.analytics.filters import load_filtered
from dashboard.analytics.trends import month_over_month, spans_multiple_years, year_over_year
from dashboard.charts import chart_card
from dashboard.components import empty_state, section, sortable_table
from dashboard.layout import page
from dashboard.palette import CATEGORICAL, SINGLE_SERIES


def register_trends_routes(rt):
    @rt("/trends")
    def get(start: str = "", end: str = ""):
        receipts_df, _, _, filter_bar = load_filtered("/trends", start, end)

        if filter_bar is None:
            return page(
                "Trends",
                empty_state("No purchase history yet. Import a JSON or CSV export to get started."),
                active="/trends",
            )

        if receipts_df.empty:
            return page(
                "Trends",
                section("No receipts in this range", "Try widening the date filter above."),
                active="/trends",
                filter_bar=filter_bar,
            )

        mom = month_over_month(receipts_df)
        fig = px.bar(mom, x="month", y="total", labels={"month": "Month", "total": "Spend ($)"})
        fig.update_traces(marker_color=SINGLE_SERIES, marker_line_width=0)
        trend_chart = chart_card(fig)

        mom_table = sortable_table(
            header_data=["Month", "Spend", "Change", "% Change"],
            body_data=[
                {
                    "Month": f"{row.month:%Y-%m}",
                    "Spend": f"${row.total:,.2f}",
                    "Change": f"${row.change:,.2f}" if row.change == row.change else "—",
                    "% Change": f"{row.pct_change:,.1f}%" if row.pct_change == row.pct_change else "—",
                }
                for row in mom.itertuples()
            ],
        )

        sections = [
            section("Monthly Spend", trend_chart, icon="bar-chart-3"),
            section("Month-over-Month", mom_table, icon="table"),
        ]

        if spans_multiple_years(receipts_df):
            yoy = year_over_year(receipts_df)
            yoy_fig = px.line(
                yoy,
                x="month_num",
                y="total",
                color="year",
                markers=True,
                labels={"month_num": "Month", "total": "Spend ($)", "year": "Year"},
                color_discrete_sequence=CATEGORICAL,
                category_orders={"year": sorted(yoy["year"].unique())},
            )
            yoy_fig.update_traces(line_width=2, marker_size=8)
            sections.append(section("Year-over-Year", chart_card(yoy_fig), icon="calendar-days"))

        return page(
            "Trends", *sections, active="/trends", subtitle="Spend patterns over time", filter_bar=filter_bar
        )
