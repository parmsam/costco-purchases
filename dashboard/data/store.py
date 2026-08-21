"""Parquet bulk cache + SQLite metadata persistence.

Parquet (data/receipts.parquet, items.parquet, tenders.parquet) is the
analytics cache: on each import we load what's on disk, concat the new
rows, dedup, and overwrite. Simple and fast at personal-purchase-history
scale — no need for incremental/transactional writes.

SQLite (data/dashboard.db, via fastlite) holds small mutable metadata:
upload_history and department_labels.
"""

from pathlib import Path

import pandas as pd
from fastlite import database

from dashboard.data.normalize import normalize_all
from dashboard.data.schema import empty_frame, ITEMS_COLUMNS, RECEIPTS_COLUMNS, TENDERS_COLUMNS

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RECEIPTS_PATH = DATA_DIR / "receipts.parquet"
ITEMS_PATH = DATA_DIR / "items.parquet"
TENDERS_PATH = DATA_DIR / "tenders.parquet"
DB_PATH = DATA_DIR / "dashboard.db"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_parquet_or_empty(path: Path, columns: dict) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return empty_frame(columns)


def load_all() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    _ensure_data_dir()
    receipts_df = _read_parquet_or_empty(RECEIPTS_PATH, RECEIPTS_COLUMNS)
    items_df = _read_parquet_or_empty(ITEMS_PATH, ITEMS_COLUMNS)
    tenders_df = _read_parquet_or_empty(TENDERS_PATH, TENDERS_COLUMNS)
    return receipts_df, items_df, tenders_df


def merge_and_save(
    new_receipts: pd.DataFrame, new_items: pd.DataFrame, new_tenders: pd.DataFrame
) -> dict:
    """Merge freshly-parsed frames into the on-disk Parquet cache.

    Dedup keys: receipt_id for receipts, (receipt_id, line_no) for items,
    (receipt_id, tender_type_name, amount_tender) for tenders.
    keep='last' so a re-import can correct previously-stale rows.

    Returns counts of rows added (post-dedup delta) for the upload_history log.
    """
    _ensure_data_dir()

    new_receipts, new_items, new_tenders = normalize_all(new_receipts, new_items, new_tenders)
    existing_receipts, existing_items, existing_tenders = load_all()

    before_receipts = len(existing_receipts)
    before_items = len(existing_items)

    receipts_df = pd.concat([existing_receipts, new_receipts], ignore_index=True)
    receipts_df = receipts_df.drop_duplicates(subset=["receipt_id"], keep="last")

    items_df = pd.concat([existing_items, new_items], ignore_index=True)
    items_df = items_df.drop_duplicates(subset=["receipt_id", "line_no"], keep="last")

    tenders_df = pd.concat([existing_tenders, new_tenders], ignore_index=True)
    tenders_df = tenders_df.drop_duplicates(
        subset=["receipt_id", "tender_type_name", "amount_tender"], keep="last"
    )

    receipts_df.to_parquet(RECEIPTS_PATH, index=False)
    items_df.to_parquet(ITEMS_PATH, index=False)
    tenders_df.to_parquet(TENDERS_PATH, index=False)

    return {
        "receipts_added": len(receipts_df) - before_receipts,
        "receipts_total": len(receipts_df),
        "items_added": len(items_df) - before_items,
        "items_total": len(items_df),
    }


# ---------------------------------------------------------------------
# SQLite metadata (fastlite)
# ---------------------------------------------------------------------


def get_db():
    _ensure_data_dir()
    db = database(DB_PATH)
    if "upload_history" not in db.t:
        db.t.upload_history.create(
            id=int,
            filename=str,
            timestamp=str,
            format=str,
            receipts_added=int,
            items_added=int,
            pk="id",
        )
    if "department_labels" not in db.t:
        db.t.department_labels.create(
            dept_number=str,
            custom_label=str,
            pk="dept_number",
        )
    if "item_labels" not in db.t:
        db.t.item_labels.create(
            item_number=str,
            custom_label=str,
            pk="item_number",
        )
    return db


def record_upload(filename: str, format: str, receipts_added: int, items_added: int):
    from datetime import datetime, timezone

    db = get_db()
    db.t.upload_history.insert(
        filename=filename,
        timestamp=datetime.now(timezone.utc).isoformat(),
        format=format,
        receipts_added=receipts_added,
        items_added=items_added,
    )


def get_upload_history() -> list[dict]:
    db = get_db()
    return list(db.t.upload_history(order_by="-id"))


def get_department_labels() -> dict:
    db = get_db()
    return {row["dept_number"]: row["custom_label"] for row in db.t.department_labels()}


def set_department_label(dept_number: str, custom_label: str):
    db = get_db()
    db.t.department_labels.upsert(dept_number=dept_number, custom_label=custom_label)


def get_item_labels() -> dict:
    db = get_db()
    return {row["item_number"]: row["custom_label"] for row in db.t.item_labels()}


def set_item_label(item_number: str, custom_label: str):
    db = get_db()
    if custom_label:
        db.t.item_labels.upsert(item_number=item_number, custom_label=custom_label)
    else:
        # Blank label clears the override, reverting to the raw description.
        try:
            db.t.item_labels.delete(item_number)
        except Exception:
            pass
