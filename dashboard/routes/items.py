"""GET /items — searchable itemized table + top-items-by-spend/frequency."""

import json

from fasthtml.common import Div, Form, Input as RawInput, Span
from monsterui.franken import A, Button, ButtonT, Input, UkIcon

from dashboard.analytics.filters import load_filtered
from dashboard.analytics.items import (
    distinct_items,
    filter_items,
    spend_column,
    top_items_by_frequency,
    top_items_by_spend,
)
from dashboard.components import empty_state, section, sortable_table
from dashboard.data.normalize import item_label
from dashboard.data.store import get_item_labels, set_item_label
from dashboard.layout import page


ITEMS_TABLE_ROW_LIMIT = 200


def _items_table_rows(filtered_df, item_labels: dict):
    # net_amount (falls back to amount for pre-net_amount parquet data) so
    # a row with instant savings shows what was actually paid, now that
    # discount lines themselves are excluded (see analytics.items.filter_items)
    # rather than appearing as their own separate "/ 1937959" row.
    amt_col = spend_column(filtered_df)
    table = sortable_table(
        header_data=["Date", "Warehouse", "Item", "Amount"],
        body_data=[
            {
                "Date": A(
                    f"{row.transaction_date:%Y-%m-%d}" if row.transaction_date is not None else "",
                    href=f"/receipt/{row.receipt_id}",
                    cls="text-primary hover:underline",
                ),
                "Warehouse": row.warehouse_name,
                "Item": item_label(row.item_number, row.item_description, item_labels),
                "Amount": f"${amt:,.2f}" if (amt := getattr(row, amt_col)) == amt else "",
            }
            for row in filtered_df.head(ITEMS_TABLE_ROW_LIMIT).itertuples()
        ],
    )

    # Count/total reflect the full filtered set, not just the rows shown
    # above (the table caps at ITEMS_TABLE_ROW_LIMIT rows) — this is meant
    # to answer "how much did these matching purchases add up to", which
    # shouldn't silently go stale once a search matches more than that cap.
    item_count = len(filtered_df)
    total_amount = filtered_df[amt_col].sum() if item_count else 0.0
    shown = min(item_count, ITEMS_TABLE_ROW_LIMIT)
    truncated_note = f" (showing first {shown})" if item_count > ITEMS_TABLE_ROW_LIMIT else ""
    summary = Div(
        Span(f"{item_count:,} item{'s' if item_count != 1 else ''}{truncated_note}", cls="text-muted-foreground"),
        Span(f"Total: ${total_amount:,.2f}", cls="font-semibold"),
        cls="flex items-center justify-between text-sm px-3 py-2 border-t border-border",
    )

    return Div(table, summary)


def _label_editor_row(item_number: str, raw_description: str, current_label: str, saved: bool = False):
    return Form(
        Div(
            Div(raw_description or "", cls="text-sm truncate"),
            Div(f"#{item_number}", cls="text-xs text-muted-foreground"),
            cls="flex-1 min-w-0",
        ),
        RawInput(type="hidden", name="item_number", value=item_number),
        Input(
            type="text",
            name="label",
            value=current_label or "",
            placeholder="Custom name (e.g. Butter Croissant)",
            cls="flex-1 min-w-0 text-sm",
        ),
        Button(
            UkIcon("check", height=14, width=14),
            "Saved" if saved else "Save",
            cls=(ButtonT.primary if not saved else ButtonT.default, "shrink-0 flex items-center gap-1 text-xs"),
            submit=True,
        ),
        hx_post="/items/label",
        hx_target="this",
        hx_swap="outerHTML",
        cls="flex items-center gap-3 py-2 border-b border-border/50",
        id=f"item-label-row-{item_number}",
    )


def _label_editor(items_df, item_labels: dict):
    rows = distinct_items(items_df)
    return Div(
        *[
            _label_editor_row(row.item_number, row.item_description, item_labels.get(row.item_number))
            for row in rows.itertuples()
        ],
        id="item-label-editor",
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

        item_labels = get_item_labels()

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
        table_div = Div(_items_table_rows(filtered, item_labels), id="items-table")
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
            section(
                "Manage Item Names",
                "Give your top items (by spend) a plain-language name — used on this page and the "
                "Dashboard's Recent Receipts. Costco's raw item codes have no public name mapping, "
                "so this is entirely up to you. Leave blank to revert to the raw description.",
                _label_editor(items_df, item_labels),
                icon="pencil",
            ),
            active="/items",
            subtitle="Every line item, searchable",
            filter_bar=filter_bar,
        )

    @rt("/items/table")
    def get(search: str = "", start: str = "", end: str = ""):
        receipts_df, items_df, _, _ = load_filtered("/items", start, end)
        filtered = filter_items(items_df, receipts_df, search=search)
        return Div(_items_table_rows(filtered, get_item_labels()), id="items-table")

    @rt("/items/label")
    def post(item_number: str, label: str = ""):
        set_item_label(item_number, label.strip())
        _, items_df, _, _ = load_filtered("/items", "", "")
        raw_description = ""
        rows = distinct_items(items_df, n=10_000)
        match = rows[rows["item_number"] == item_number]
        if not match.empty:
            raw_description = match.iloc[0]["item_description"]
        return _label_editor_row(item_number, raw_description, label.strip(), saved=True)
