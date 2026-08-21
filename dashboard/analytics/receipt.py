"""Single-receipt lookup for the /receipt/{receipt_id} detail view."""

import pandas as pd


def get_receipt(
    receipts_df: pd.DataFrame, items_df: pd.DataFrame, tenders_df: pd.DataFrame, receipt_id: str
) -> dict | None:
    match = receipts_df[receipts_df["receipt_id"] == receipt_id]
    if match.empty:
        return None

    receipt = match.iloc[0].to_dict()
    receipt["items"] = (
        items_df[items_df["receipt_id"] == receipt_id].sort_values("line_no").to_dict("records")
    )
    receipt["tenders"] = tenders_df[tenders_df["receipt_id"] == receipt_id].to_dict("records")
    return receipt
