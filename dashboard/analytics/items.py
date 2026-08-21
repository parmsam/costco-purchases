"""Item-level analytics: top items by spend/frequency, search+filter for the table view."""

import pandas as pd


def _exclude_discounts(items_df: pd.DataFrame) -> pd.DataFrame:
    if "is_discount" not in items_df.columns:
        return items_df
    return items_df[~items_df["is_discount"].fillna(False)]


def top_items_by_spend(items_df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if items_df.empty:
        return pd.DataFrame(columns=["item_description", "total_spend", "purchase_count"])
    grouped = _exclude_discounts(items_df).groupby("item_description", as_index=False).agg(
        total_spend=("amount", "sum"), purchase_count=("amount", "count")
    )
    return grouped.sort_values("total_spend", ascending=False).head(n)


def top_items_by_frequency(items_df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if items_df.empty:
        return pd.DataFrame(columns=["item_description", "purchase_count", "total_spend"])
    grouped = _exclude_discounts(items_df).groupby("item_description", as_index=False).agg(
        purchase_count=("amount", "count"), total_spend=("amount", "sum")
    )
    return grouped.sort_values("purchase_count", ascending=False).head(n)


def filter_items(items_df: pd.DataFrame, receipts_df: pd.DataFrame, search: str = "") -> pd.DataFrame:
    merged = items_df.merge(
        receipts_df[["receipt_id", "transaction_date", "warehouse_name"]],
        on="receipt_id",
        how="left",
    )
    if search:
        mask = merged["item_description"].fillna("").str.contains(search, case=False, regex=False)
        merged = merged[mask]
    return merged.sort_values("transaction_date", ascending=False)
