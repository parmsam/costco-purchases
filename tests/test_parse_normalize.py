import pandas as pd

from dashboard.data.normalize import normalize_all
from dashboard.data.parse_csv import parse_csv
from dashboard.data.parse_json import parse_json
from tests.fixtures import SAMPLE_ITEM_CSV, SAMPLE_RECEIPT_CSV, SAMPLE_RECEIPTS_JSON


def _sorted_reset(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    return df.sort_values(by).reset_index(drop=True)


def test_parse_json_shapes():
    receipts_df, items_df, tenders_df = parse_json(SAMPLE_RECEIPTS_JSON)
    assert len(receipts_df) == 2
    assert len(items_df) == 3
    assert len(tenders_df) == 2
    assert set(receipts_df["receipt_id"]) == {
        "111122223333__AAA111",
        "111122223333__BBB222",
    }


def test_parse_csv_shapes():
    receipts_df, items_df, tenders_df = parse_csv(
        item_csv=SAMPLE_ITEM_CSV, receipt_csv=SAMPLE_RECEIPT_CSV
    )
    assert len(receipts_df) == 2
    assert len(items_df) == 3
    assert tenders_df.empty


def test_json_and_csv_normalize_to_equivalent_frames():
    json_receipts, json_items, json_tenders = normalize_all(*parse_json(SAMPLE_RECEIPTS_JSON))
    csv_receipts, csv_items, csv_tenders = normalize_all(
        *parse_csv(item_csv=SAMPLE_ITEM_CSV, receipt_csv=SAMPLE_RECEIPT_CSV)
    )

    shared_receipt_cols = [
        "receipt_id",
        "membership_number",
        "transaction_barcode",
        "transaction_date",
        "warehouse_name",
        "total",
        "subtotal",
        "taxes",
        "instant_savings",
        "total_item_count",
    ]
    json_r = _sorted_reset(json_receipts[shared_receipt_cols], ["receipt_id"])
    csv_r = _sorted_reset(csv_receipts[shared_receipt_cols], ["receipt_id"])
    pd.testing.assert_frame_equal(json_r, csv_r)

    shared_item_cols = [
        "receipt_id",
        "item_number",
        "item_description",
        "item_department_number",
        "amount",
        "unit_price",
    ]
    json_i = _sorted_reset(json_items[shared_item_cols], ["receipt_id", "item_number"])
    csv_i = _sorted_reset(csv_items[shared_item_cols], ["receipt_id", "item_number"])
    pd.testing.assert_frame_equal(json_i, csv_i)

    # tenders_df is JSON-only by design.
    assert csv_tenders.empty
    assert not json_tenders.empty


def test_csv_item_level_only_derives_receipts():
    receipts_df, items_df, _ = parse_csv(item_csv=SAMPLE_ITEM_CSV)
    assert len(receipts_df) == 2
    assert set(receipts_df["total_item_count"]) == {1, 2}
