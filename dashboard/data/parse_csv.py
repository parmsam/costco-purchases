"""Parse item-level and/or receipt-level CSV exports into normalized frames.

Column names here mirror the headers produced by
``downloader/costco_receipt_downloader.js`` (``toItemLevelCSV`` /
``toReceiptLevelCSV``): the receipt-level fields repeated on every item
row, plus item-only fields on the item CSV.
"""

import io

import pandas as pd

from dashboard.data.schema import ITEMS_COLUMNS, RECEIPTS_COLUMNS, TENDERS_COLUMNS, empty_frame

_RECEIPT_CSV_TO_CANONICAL = {
    "transactionDate": "transaction_date",
    "warehouseName": "warehouse_name",
    "warehouseShortName": "warehouse_short_name",
    "warehouseCity": "warehouse_city",
    "warehouseState": "warehouse_state",
    "membershipNumber": "membership_number",
    "transactionBarcode": "transaction_barcode",
    "total": "total",
    "subTotal": "subtotal",
    "taxes": "taxes",
    "instantSavings": "instant_savings",
    "totalItemCount": "total_item_count",
}

_ITEM_CSV_TO_CANONICAL = {
    "itemNumber": "item_number",
    "itemDepartmentNumber": "item_department_number",
    "itemUnitPriceAmount": "unit_price",
    "unit": "unit",
    "amount": "amount",
    "taxFlag": "tax_flag",
    "refundFlag": "refund_flag",
    "voidFlag": "void_flag",
    "entryMethod": "entry_method",
}


def _read_csv(csv_input) -> pd.DataFrame:
    if isinstance(csv_input, (bytes, bytearray)):
        csv_input = io.BytesIO(csv_input)
    elif isinstance(csv_input, str):
        csv_input = io.StringIO(csv_input)
    return pd.read_csv(csv_input, dtype=str)


def _receipt_id_from_row(row) -> str:
    return f"{row.get('membershipNumber')}__{row.get('transactionBarcode')}"


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def parse_receipt_level_csv(csv_input) -> pd.DataFrame:
    raw = _read_csv(csv_input)
    if raw.empty:
        return empty_frame(RECEIPTS_COLUMNS)

    df = pd.DataFrame()
    df["receipt_id"] = raw.apply(_receipt_id_from_row, axis=1)
    for csv_col, canonical_col in _RECEIPT_CSV_TO_CANONICAL.items():
        df[canonical_col] = raw.get(csv_col)

    for col in ("total", "subtotal", "taxes", "instant_savings", "total_item_count"):
        df[col] = _numeric(df[col])

    df["source"] = "csv"
    return df


def parse_item_level_csv(csv_input) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (receipts_df, items_df) derived from the item-level CSV.

    receipts_df here is derived (one row per distinct receipt_id, taking
    the first item row's receipt fields) — callers should prefer a
    receipt-level CSV as authoritative when one is also available.
    """
    raw = _read_csv(csv_input)
    if raw.empty:
        return empty_frame(RECEIPTS_COLUMNS), empty_frame(ITEMS_COLUMNS)

    raw["receipt_id"] = raw.apply(_receipt_id_from_row, axis=1)

    receipt_cols = pd.DataFrame()
    receipt_cols["receipt_id"] = raw["receipt_id"]
    for csv_col, canonical_col in _RECEIPT_CSV_TO_CANONICAL.items():
        if csv_col in raw.columns:
            receipt_cols[canonical_col] = raw[csv_col]
    receipts_df = receipt_cols.groupby("receipt_id", as_index=False).first()
    for col in ("total", "subtotal", "taxes", "instant_savings"):
        if col in receipts_df.columns:
            receipts_df[col] = _numeric(receipts_df[col])
    receipts_df["total_item_count"] = receipts_df["receipt_id"].map(
        raw.groupby("receipt_id").size()
    )
    receipts_df["source"] = "csv"

    items_df = pd.DataFrame()
    items_df["receipt_id"] = raw["receipt_id"]
    items_df["line_no"] = raw.groupby("receipt_id").cumcount()
    for csv_col, canonical_col in _ITEM_CSV_TO_CANONICAL.items():
        if csv_col in raw.columns:
            items_df[canonical_col] = raw[csv_col]
    desc1 = raw.get("itemDescription01")
    desc2 = raw.get("itemDescription02")
    if desc1 is not None or desc2 is not None:
        items_df["item_description"] = (
            (desc1.fillna("") if desc1 is not None else "")
            + " "
            + (desc2.fillna("") if desc2 is not None else "")
        ).str.strip()
        items_df.loc[items_df["item_description"] == "", "item_description"] = None
    if desc1 is not None:
        items_df["item_description_primary"] = desc1

    for col in ("amount", "unit_price"):
        if col in items_df.columns:
            items_df[col] = _numeric(items_df[col])
    for col in ("tax_flag", "refund_flag", "void_flag"):
        if col in items_df.columns:
            items_df[col] = items_df[col].map(
                {"true": True, "false": False, "True": True, "False": False}
            )

    return receipts_df, items_df


def parse_csv(
    item_csv=None, receipt_csv=None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Combine item-level and/or receipt-level CSV input into normalized frames.

    The receipt-level CSV is authoritative for receipts_df when provided
    (it correctly covers edge cases like all-void receipts that have no
    surviving item rows). tenders_df is always empty for CSV input.
    """
    if item_csv is None and receipt_csv is None:
        raise ValueError("parse_csv requires at least one of item_csv or receipt_csv")

    items_df = empty_frame(ITEMS_COLUMNS)
    derived_receipts_df = None

    if item_csv is not None:
        derived_receipts_df, items_df = parse_item_level_csv(item_csv)

    if receipt_csv is not None:
        receipts_df = parse_receipt_level_csv(receipt_csv)
    else:
        receipts_df = derived_receipts_df if derived_receipts_df is not None else empty_frame(
            RECEIPTS_COLUMNS
        )

    tenders_df = empty_frame(TENDERS_COLUMNS)
    return receipts_df, items_df, tenders_df
