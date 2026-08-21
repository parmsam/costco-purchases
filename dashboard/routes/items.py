"""GET /items — searchable itemized table + top-items-by-spend/frequency."""

import json

from fasthtml.common import Div
from monsterui.franken import A, Input, UkIcon

from dashboard.analytics.filters import load_filtered
from dashboard.analytics.items import filter_items, top_items_by_frequency, top_items_by_spend
from dashboard.components import empty_state, section, sortable_table
from dashboard.layout import page


def _items_table_rows(filtered_df):
    return sortable_table(
        header_data=["Date", "Warehouse", "Item", "Amount"],
        body_data=[
            {
                "Date": A(
                    f"{row.transaction_date:%Y-%m-%d}" if row.transaction_date is not None else "",
                    href=f"/receipt/{row.receipt_id}",
                    cls="text-primary hover:underline",
                ),
                "Warehouse": row.warehouse_name,
                "Item": row.item_description,
                "Amount": f"${row.amount:,.2f}" if row.amount == row.amount else "",
            }
            for row in filtered_df.head(200).itertuples()
        ],
    )


def register_items_routes(rt):
    @rt("/items")
    def get(start: str = "", end: str = ""):
        receipts_df, items_df, _, filter_bar = load_filtered("/items", start, end)

        if filter_bar is None:
            return page(
                "Items",
                empty_state("No purchase history yet. Import a JSON or CSV export to get started."),
                active="/items",
            )

        if items_df.empty:
            return page(
                "Items",
                section("No items in this range", "Try widening the date filter above."),
                active="/items",
                filter_bar=filter_bar,
            )

        top_spend = top_items_by_spend(items_df)
        top_freq = top_items_by_frequency(items_df)

        top_spend_table = sortable_table(
            header_data=["Item", "Total Spend", "Purchases"],
            body_data=[
                {
                    "Item": row.item_description,
                    "Total Spend": f"${row.total_spend:,.2f}",
                    "Purchases": row.purchase_count,
                }
                for row in top_spend.itertuples()
            ],
        )
        top_freq_table = sortable_table(
            header_data=["Item", "Purchases", "Total Spend"],
            body_data=[
                {
                    "Item": row.item_description,
                    "Purchases": row.purchase_count,
                    "Total Spend": f"${row.total_spend:,.2f}",
                }
                for row in top_freq.itertuples()
            ],
        )

        filtered = filter_items(items_df, receipts_df)
        table_div = Div(_items_table_rows(filtered), id="items-table")
        search_box = Div(
            UkIcon("search", height=16, width=16, cls="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"),
            Input(
                type="search",
                name="search",
                placeholder="Search items...",
                hx_get="/items/table",
                hx_trigger="input changed delay:300ms, search",
                hx_target="#items-table",
                hx_vals=json.dumps({"start": start, "end": end}),
                cls="pl-9",
            ),
            cls="relative mb-4 max-w-md",
        )

        return page(
            "Items",
            section("Search Purchases", search_box, table_div, icon="search"),
            section("Top Items by Spend", top_spend_table, icon="trending-up"),
            section("Top Items by Frequency", top_freq_table, icon="repeat"),
            active="/items",
            subtitle="Every line item, searchable",
            filter_bar=filter_bar,
        )

    @rt("/items/table")
    def get(search: str = "", start: str = "", end: str = ""):
        receipts_df, items_df, _, _ = load_filtered("/items", start, end)
        filtered = filter_items(items_df, receipts_df, search=search)
        return Div(_items_table_rows(filtered), id="items-table")
