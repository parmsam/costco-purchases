"""Payment-method breakdown analytics. tenders_df is JSON-only; may be empty."""

import pandas as pd


def spend_by_payment_method(tenders_df: pd.DataFrame) -> pd.DataFrame:
    if tenders_df.empty:
        return pd.DataFrame(columns=["tender_type_name", "total"])
    return (
        tenders_df.groupby("tender_type_name", as_index=False)["amount_tender"]
        .sum()
        .rename(columns={"amount_tender": "total"})
        .sort_values("total", ascending=False)
    )


def payment_method_details(tenders_df: pd.DataFrame) -> pd.DataFrame:
    """Per-method spend, transaction count, average, and share of total spend."""
    if tenders_df.empty:
        return pd.DataFrame(columns=["tender_type_name", "total", "count", "avg", "pct"])
    grouped = tenders_df.groupby("tender_type_name", as_index=False).agg(
        total=("amount_tender", "sum"), count=("amount_tender", "count")
    )
    grouped["avg"] = grouped["total"] / grouped["count"]
    total_all = grouped["total"].sum()
    grouped["pct"] = (grouped["total"] / total_all * 100) if total_all else 0.0
    return grouped.sort_values("total", ascending=False)


def payment_kpis(tenders_df: pd.DataFrame) -> dict:
    if tenders_df.empty:
        return {
            "transaction_count": 0,
            "method_count": 0,
            "top_method": "—",
            "top_method_pct": 0.0,
            "avg_transaction": 0.0,
        }
    details = payment_method_details(tenders_df)
    top = details.iloc[0]
    return {
        "transaction_count": len(tenders_df),
        "method_count": tenders_df["tender_type_name"].nunique(),
        "top_method": top["tender_type_name"],
        "top_method_pct": top["pct"],
        "avg_transaction": tenders_df["amount_tender"].mean(),
    }


def monthly_spend_by_method(tenders_df: pd.DataFrame, receipts_df: pd.DataFrame) -> pd.DataFrame:
    """Spend per month per payment method, for a stacked trend chart."""
    if tenders_df.empty or receipts_df.empty:
        return pd.DataFrame(columns=["month", "tender_type_name", "total"])
    merged = tenders_df.merge(
        receipts_df[["receipt_id", "transaction_date"]], on="receipt_id", how="left"
    ).dropna(subset=["transaction_date"])
    merged["month"] = merged["transaction_date"].dt.to_period("M").dt.to_timestamp()
    return (
        merged.groupby(["month", "tender_type_name"], as_index=False)["amount_tender"]
        .sum()
        .rename(columns={"amount_tender": "total"})
    )
