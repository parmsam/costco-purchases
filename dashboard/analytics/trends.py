"""Monthly / yearly spend trend computations."""

import pandas as pd


def monthly_spend(receipts_df: pd.DataFrame) -> pd.DataFrame:
    if receipts_df.empty:
        return pd.DataFrame(columns=["month", "total"])
    df = receipts_df.dropna(subset=["transaction_date"]).copy()
    df["month"] = df["transaction_date"].dt.to_period("M").dt.to_timestamp()
    out = df.groupby("month", as_index=False)["total"].sum().sort_values("month")
    return out


def month_over_month(receipts_df: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly_spend(receipts_df)
    if monthly.empty:
        return monthly.assign(change=[], pct_change=[])
    monthly = monthly.copy()
    monthly["change"] = monthly["total"].diff()
    monthly["pct_change"] = monthly["total"].pct_change() * 100
    return monthly


def year_over_year(receipts_df: pd.DataFrame) -> pd.DataFrame:
    if receipts_df.empty:
        return pd.DataFrame(columns=["year", "month_num", "total"])
    df = receipts_df.dropna(subset=["transaction_date"]).copy()
    df["year"] = df["transaction_date"].dt.year
    df["month_num"] = df["transaction_date"].dt.month
    return df.groupby(["year", "month_num"], as_index=False)["total"].sum()


def spans_multiple_years(receipts_df: pd.DataFrame) -> bool:
    if receipts_df.empty:
        return False
    dates = receipts_df["transaction_date"].dropna()
    return dates.dt.year.nunique() > 1
