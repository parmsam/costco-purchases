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


def distinct_items(items_df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    """One row per item_number (raw description + total spend), for the
    'Manage Item Names' editor — sorted by spend so the items worth naming
    are easy to find first. item_number isn't unique-per-row (discount
    lines reuse the linked item's number), so this only considers real
    purchase rows.
    """
    if items_df.empty:
        return pd.DataFrame(columns=["item_number", "item_description", "total_spend"])
    real = _exclude_discounts(items_df).dropna(subset=["item_number"])
    grouped = real.groupby("item_number", as_index=False).agg(
        item_description=("item_description", "first"),
        total_spend=("amount", "sum"),
    )
    return grouped.sort_values("total_spend", ascending=False).head(n)


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
