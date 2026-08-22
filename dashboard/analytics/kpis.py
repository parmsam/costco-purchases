"""Top-line KPI computations for the /dashboard overview."""

import pandas as pd


def compute_kpis(receipts_df: pd.DataFrame, items_df: pd.DataFrame | None = None) -> dict:
    if receipts_df.empty:
        kpis = {
            "total_spend": 0.0,
            "receipt_count": 0,
            "date_range": "—",
            "avg_basket": 0.0,
            "total_instant_savings": 0.0,
            "avg_items_per_receipt": 0.0,
        }
    else:
        total_spend = receipts_df["total"].sum()
        receipt_count = len(receipts_df)
        min_date = receipts_df["transaction_date"].min()
        max_date = receipts_df["transaction_date"].max()
        date_range = f"{min_date:%b %Y} – {max_date:%b %Y}" if pd.notna(min_date) else "—"

        kpis = {
            "total_spend": total_spend,
            "receipt_count": receipt_count,
            "date_range": date_range,
            "avg_basket": total_spend / receipt_count if receipt_count else 0.0,
            "total_instant_savings": receipts_df["instant_savings"].sum(),
            "avg_items_per_receipt": receipts_df["total_item_count"].mean() or 0.0,
        }

    # Cross-check: sum of discount line items (see normalize.is_discount)
    # vs. the receipt-level instant_savings field above. They should
    # roughly agree; a persistent gap would flag a parsing issue.
    if items_df is not None and not items_df.empty and "is_discount" in items_df.columns:
        discount_rows = items_df[items_df["is_discount"].fillna(False)]
        kpis["instant_savings_line_items"] = -discount_rows["amount"].sum()
        real_items = items_df[~items_df["is_discount"].fillna(False)]
        kpis["unique_items"] = int(real_items["item_number"].dropna().nunique())
    else:
        kpis["instant_savings_line_items"] = 0.0
        kpis["unique_items"] = 0

    return kpis
