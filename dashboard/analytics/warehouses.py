"""Spend-by-warehouse analytics."""

import pandas as pd


def spend_by_warehouse(receipts_df: pd.DataFrame) -> pd.DataFrame:
    if receipts_df.empty:
        return pd.DataFrame(columns=["warehouse_name", "total_spend", "visits", "avg_basket"])
    grouped = receipts_df.groupby("warehouse_name", as_index=False).agg(
        total_spend=("total", "sum"), visits=("receipt_id", "count")
    )
    grouped["avg_basket"] = grouped["total_spend"] / grouped["visits"]
    return grouped.sort_values("total_spend", ascending=False)
