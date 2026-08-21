"""Spend-by-department analytics."""

import pandas as pd

from dashboard.data.normalize import department_label


def spend_by_department(items_df: pd.DataFrame, overrides: dict | None = None) -> pd.DataFrame:
    if items_df.empty:
        return pd.DataFrame(columns=["item_department_number", "label", "total_spend", "item_count", "sample_items"])

    grouped = items_df.groupby("item_department_number", as_index=False).agg(
        total_spend=("amount", "sum"), item_count=("amount", "count")
    )
    grouped["label"] = grouped["item_department_number"].apply(
        lambda d: department_label(d, overrides)
    )

    samples = (
        items_df.dropna(subset=["item_description"])
        .groupby("item_department_number")["item_description"]
        .apply(lambda s: ", ".join(s.drop_duplicates().head(3)))
    )
    grouped["sample_items"] = grouped["item_department_number"].map(samples).fillna("")

    return grouped.sort_values("total_spend", ascending=False)
