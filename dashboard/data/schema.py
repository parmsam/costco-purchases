"""Canonical column lists and dtypes for the three normalized DataFrames.

Every ingestion path (JSON export, item-level CSV, receipt-level CSV) ends
up reindexed to exactly these columns so downstream analytics code never
has to branch on where the data came from.
"""

import pandas as pd

RECEIPTS_COLUMNS = {
    "receipt_id": "string",
    "membership_number": "string",
    "transaction_barcode": "string",
    "transaction_date": "datetime64[ns]",
    "transaction_datetime": "datetime64[ns]",
    "warehouse_name": "string",
    "warehouse_short_name": "string",
    "warehouse_number": "string",
    "warehouse_city": "string",
    "warehouse_state": "string",
    "warehouse_address1": "string",
    "warehouse_address2": "string",
    "warehouse_postal_code": "string",
    "total": "float64",
    "subtotal": "float64",
    "taxes": "float64",
    "instant_savings": "float64",
    "total_item_count": "Int64",
    "register_number": "string",
    "transaction_number": "string",
    "operator_number": "string",
    "source": "string",
}

ITEMS_COLUMNS = {
    "receipt_id": "string",
    "line_no": "Int64",
    "item_number": "string",
    "item_description": "string",
    # itemDescription01 alone (no itemDescription02 appended) — matches the
    # single line Costco prints on the actual receipt; item_description above
    # is the fuller, merged text used for search/analytics.
    "item_description_primary": "string",
    "item_department_number": "string",
    "amount": "float64",
    "unit_price": "float64",
    "unit": "string",
    # Costco's own API returns "Y"/"N" (not real booleans) for these flags,
    # so they're kept as raw strings and printed as-is on the receipt view.
    "tax_flag": "string",
    "refund_flag": "string",
    "void_flag": "string",
    "is_discount": "boolean",
    "entry_method": "string",
    "coupon_amount": "float64",
    "fuel_unit_quantity": "float64",
    "fuel_grade_code": "string",
    "fuel_uom_code": "string",
}

TENDERS_COLUMNS = {
    "receipt_id": "string",
    "tender_type_name": "string",
    "amount_tender": "float64",
    "wallet_type": "string",
    "display_account_number": "string",
    "approval_number": "string",
    "entry_method": "string",
}


def empty_frame(columns: dict) -> pd.DataFrame:
    """Build an empty, correctly-typed DataFrame for one of the schemas above."""
    df = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in columns.items()})
    return df


def coerce_schema(df: pd.DataFrame, columns: dict) -> pd.DataFrame:
    """Reindex df to the canonical column set/order and coerce dtypes.

    Missing columns are filled with NA; extra columns are dropped.
    """
    df = df.reindex(columns=list(columns.keys()))
    for col, dtype in columns.items():
        if dtype == "datetime64[ns]":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            try:
                df[col] = df[col].astype(dtype)
            except (TypeError, ValueError):
                df[col] = df[col]
    return df
