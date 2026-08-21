"""GET /departments — spend by Dept #NNNN (chart + table), respecting custom labels."""

import pandas as pd
import plotly.express as px

from dashboard.analytics.departments import spend_by_department
from dashboard.analytics.filters import load_filtered
from dashboard.charts import chart_card
from dashboard.components import empty_state, section, sortable_table
from dashboard.data.store import get_department_labels
from dashboard.layout import page
from dashboard.palette import SINGLE_SERIES

CHART_TOP_N = 10


def _chart_data(by_dept: pd.DataFrame) -> pd.DataFrame:
    """Top N departments by spend for the chart; long tail folds into 'Other'."""
    if len(by_dept) <= CHART_TOP_N:
        return by_dept
    top = by_dept.head(CHART_TOP_N)
    rest = by_dept.iloc[CHART_TOP_N:]
    other_row = pd.DataFrame(
        [{"label": f"Other ({len(rest)} depts)", "total_spend": rest["total_spend"].sum()}]
    )
    return pd.concat([top[["label", "total_spend"]], other_row], ignore_index=True)


def register_departments_routes(rt):
    @rt("/departments")
    def get(start: str = "", end: str = ""):
        _, items_df, _, filter_bar = load_filtered("/departments", start, end)

        if filter_bar is None:
            return page(
                "Departments",
                empty_state("No purchase history yet. Import a JSON or CSV export to get started."),
                active="/departments",
            )

        if items_df.empty:
            return page(
                "Departments",
                section("No receipts in this range", "Try widening the date filter above."),
                active="/departments",
                filter_bar=filter_bar,
            )

        overrides = get_department_labels()
        by_dept = spend_by_department(items_df, overrides)
        chart_data = _chart_data(by_dept).sort_values("total_spend")

        fig = px.bar(
            chart_data,
            x="total_spend",
            y="label",
            orientation="h",
            labels={"label": "", "total_spend": "Spend ($)"},
        )
        fig.update_traces(marker_color=SINGLE_SERIES, marker_line_width=0)
        chart = chart_card(fig, height=max(280, 34 * len(chart_data)))

        table = sortable_table(
            header_data=["Department", "Spend", "Items", "Sample Items"],
            body_data=[
                {
                    "Department": row.label,
                    "Spend": f"${row.total_spend:,.2f}",
                    "Items": row.item_count,
                    "Sample Items": row.sample_items,
                }
                for row in by_dept.itertuples()
            ],
        )

        return page(
            "Departments",
            section("Spend by Department", chart, icon="bar-chart-3"),
            section("Details", table, icon="table"),
            active="/departments",
            subtitle="Where your money goes by Costco department code",
            filter_bar=filter_bar,
        )
