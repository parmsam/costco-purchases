"""Reindex parsed frames to the canonical schema and coerce dtypes.

After this step, a JSON-derived and CSV-derived DataFrame for the same
underlying purchase are equivalent (columns absent from CSV, e.g.
``coupon_amount``, are simply NA).
"""

import re

import pandas as pd

from dashboard.data.schema import ITEMS_COLUMNS, RECEIPTS_COLUMNS, TENDERS_COLUMNS, coerce_schema

# Costco prints in-warehouse instant-savings/coupon deductions as their own
# item-array row, directly under the item they discount, with a "/"-prefixed
# reference as the "description" instead of a product name (usually the
# linked item number, e.g. "/ 1937959", but sometimes a short label like
# "/SNAPS" or "/ GLASSES") and a negative amount. They're real line items
# (already correctly netted into totals/department/warehouse spend) but
# pollute item-description-based groupings like "top items", so they're
# flagged here for those views to filter out. Genuine refund/return lines
# (e.g. "BATTERY DISP REFND/") keep a real product description and don't
# start with "/", so they're deliberately not matched here.
DISCOUNT_DESCRIPTION_PATTERN = re.compile(r"^/\s*\S+$")


def _attribute_discounts(df: pd.DataFrame) -> pd.Series:
    """Net each discount line's (negative) amount onto the item it discounts.

    A discount line's own description is a "/"-prefixed reference, not a
    product name (see DISCOUNT_DESCRIPTION_PATTERN above) - sometimes the
    linked item's number (e.g. "/ 1937959"), sometimes a short label like
    "/SNAPS" that doesn't identify the item at all. Rather than parse that
    reference, this uses print order instead: Costco always prints a
    discount directly under the item it applies to, and item rows are
    already in that order via line_no, so the nearest preceding
    non-discount row in the same receipt is the target. This works
    uniformly for both description styles and handles multiple stacked
    discounts (e.g. instant savings + a coupon) on the same item.
    """
    net = df["amount"].copy()
    for _, group in df.sort_values("line_no").groupby("receipt_id", sort=False):
        target_idx = None
        for idx, row in group.iterrows():
            if row["is_discount"]:
                if target_idx is not None and pd.notna(row["amount"]):
                    net.loc[target_idx] += row["amount"]
            else:
                target_idx = idx
    return net


def normalize_receipts(df: pd.DataFrame) -> pd.DataFrame:
    return coerce_schema(df, RECEIPTS_COLUMNS)


def normalize_items(df: pd.DataFrame) -> pd.DataFrame:
    df = coerce_schema(df, ITEMS_COLUMNS)
    df["is_discount"] = df["item_description"].fillna("").str.match(DISCOUNT_DESCRIPTION_PATTERN)
    df["net_amount"] = _attribute_discounts(df)
    return df


def normalize_tenders(df: pd.DataFrame) -> pd.DataFrame:
    return coerce_schema(df, TENDERS_COLUMNS)


def department_label(dept_number, overrides: dict | None = None) -> str:
    """Default 'Dept #NNNN' label, or the SQLite-stored custom override if set."""
    if dept_number is None or (isinstance(dept_number, float) and pd.isna(dept_number)):
        return "Dept #Unknown"
    if overrides and dept_number in overrides:
        return overrides[dept_number]
    return f"Dept #{dept_number}"


def item_label(item_number, raw_description: str | None, overrides: dict | None = None) -> str:
    """The user's custom plain-language name for an item_number, or the raw
    receipt description (e.g. "KS ORG EGGS") if no override is set.

    Costco's own item codes have no public code->name mapping (unlike
    department codes there's no reliable third-party list either), so this
    is entirely user-maintained via the /items "Manage Item Names" editor.
    """
    if overrides and item_number in overrides:
        return overrides[item_number]
    return raw_description or ""


def normalize_all(
    receipts_df: pd.DataFrame, items_df: pd.DataFrame, tenders_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        normalize_receipts(receipts_df),
        normalize_items(items_df),
        normalize_tenders(tenders_df),
    )
