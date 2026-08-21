"""Shared date-range filtering, applied before any other analytics runs."""

import pandas as pd

from dashboard.components import date_range_filter
from dashboard.data.store import load_all


def parse_date(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    return ts if pd.notna(ts) else None


def filter_receipts_by_date(
    receipts_df: pd.DataFrame, start: pd.Timestamp | None, end: pd.Timestamp | None
) -> pd.DataFrame:
    if receipts_df.empty:
        return receipts_df
    mask = pd.Series(True, index=receipts_df.index)
    if start is not None:
        mask &= receipts_df["transaction_date"] >= start
    if end is not None:
        mask &= receipts_df["transaction_date"] <= end
    return receipts_df[mask]


def filter_by_receipt_ids(df: pd.DataFrame, receipt_ids) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["receipt_id"].isin(receipt_ids)]


def date_bounds(receipts_df: pd.DataFrame) -> tuple[str, str] | tuple[None, None]:
    """Min/max transaction_date across all data (unfiltered), for date-input bounds."""
    if receipts_df.empty:
        return None, None
    dates = receipts_df["transaction_date"].dropna()
    if dates.empty:
        return None, None
    return f"{dates.min():%Y-%m-%d}", f"{dates.max():%Y-%m-%d}"


def load_filtered(path: str, start: str = "", end: str = ""):
    """Load all data, apply the ?start=&end= date filter, and build the filter bar.

    Returns (receipts_df, items_df, tenders_df, filter_bar) where the three
    frames are already sliced to the requested date range and to only the
    matching receipt_ids. Callers should check receipts_df.empty themselves
    to distinguish "no data at all" (point at Upload) from "no data in this
    range" (still show filter_bar so the user can widen it).
    """
    all_receipts, all_items, all_tenders = load_all()
    min_date, max_date = date_bounds(all_receipts)

    start_ts = parse_date(start)
    end_ts = parse_date(end)
    receipts_df = filter_receipts_by_date(all_receipts, start_ts, end_ts)
    receipt_ids = receipts_df["receipt_id"]
    items_df = filter_by_receipt_ids(all_items, receipt_ids)
    tenders_df = filter_by_receipt_ids(all_tenders, receipt_ids)

    filter_bar = (
        date_range_filter(path, start=start, end=end, min_date=min_date, max_date=max_date)
        if not all_receipts.empty
        else None
    )

    return receipts_df, items_df, tenders_df, filter_bar
