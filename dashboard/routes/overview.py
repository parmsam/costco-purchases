"""GET /dashboard — KPI cards + monthly trend + recent receipts."""

import plotly.express as px

from fasthtml.common import Div, Span
from monsterui.franken import A, Accordion, AccordionItem

from dashboard.analytics.filters import load_filtered
from dashboard.analytics.kpis import compute_kpis
from dashboard.analytics.receipt import get_receipt
from dashboard.analytics.trends import monthly_spend
from dashboard.charts import chart_card
from dashboard.components import empty_state, kpi_card, kpi_row, limit_select, section
from dashboard.data.store import get_upload_history
from dashboard.layout import page
from dashboard.palette import SINGLE_SERIES


def _receipt_accordion_item(receipt: dict):
    when = receipt.get("transaction_date")
    date_str = f"{when:%Y-%m-%d}" if when is not None else ""

    title = Div(
        Span(date_str, cls="w-24 shrink-0 text-sm"),
        Span(receipt.get("warehouse_name") or "", cls="flex-1 text-sm text-left truncate"),
        Span(f"${receipt['total']:,.2f}", cls="w-20 shrink-0 text-right text-sm font-semibold"),
        cls="flex items-center gap-4 flex-1 pr-2",
    )

    item_rows = [
        Div(
            Span(
                item.get("item_description_primary") or item.get("item_description") or "",
                cls="flex-1 truncate",
            ),
            Span(f"${item['amount']:,.2f}" if item.get("amount") is not None else "", cls="w-20 text-right shrink-0"),
            cls="flex text-sm py-0.5 text-muted-foreground",
        )
        for item in receipt.get("items", [])
        if not item.get("is_discount")
    ]

    savings = receipt.get("instant_savings")
    tenders = receipt.get("tenders", [])
    tender_line = ", ".join(
        f"{t.get('tender_type_name')} ${t.get('amount_tender'):,.2f}"
        for t in tenders
        if t.get("tender_type_name") is not None
    )

    content = Div(
        *item_rows,
        Div(f"Instant Savings: ${savings:,.2f}", cls="text-xs text-primary mt-2") if savings else "",
        Div(tender_line, cls="text-xs text-muted-foreground mt-1") if tender_line else "",
        A(
            "View Full Receipt →",
            href=f"/receipt/{receipt['receipt_id']}",
            cls="text-xs text-primary hover:underline mt-2 inline-block",
        ),
        cls="pt-2 pb-3",
    )

    return AccordionItem(title, content)


def register_overview_routes(rt):
    @rt("/dashboard")
    def get(start: str = "", end: str = "", limit: int = 10):
        receipts_df, items_df, tenders_df, filter_bar = load_filtered("/dashboard", start, end)

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

        sorted_ids = receipts_df.sort_values("transaction_date", ascending=False)["receipt_id"]
        recent_ids = sorted_ids if limit == 0 else sorted_ids.head(limit)
        recent_receipts = [get_receipt(receipts_df, items_df, tenders_df, rid) for rid in recent_ids]
        recent_accordion = Accordion(
            *[_receipt_accordion_item(r) for r in recent_receipts if r is not None],
            multiple=True,
        )
        recent_count_control = limit_select(
            "/dashboard", limit, [5, 10, 25, 50], {"start": start, "end": end}
        )

        return page(
            "Dashboard",
            cards,
            section("Monthly Spend", trend_chart, icon="bar-chart-3"),
            section("Recent Receipts", recent_accordion, icon="clock", controls=recent_count_control),
            active="/dashboard",
            subtitle=subtitle,
            filter_bar=filter_bar,
        )
