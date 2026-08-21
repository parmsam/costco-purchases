from dashboard.data import store
from dashboard.data.parse_json import parse_json
from tests.fixtures import SAMPLE_RECEIPTS_JSON


def _isolate_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "RECEIPTS_PATH", tmp_path / "receipts.parquet")
    monkeypatch.setattr(store, "ITEMS_PATH", tmp_path / "items.parquet")
    monkeypatch.setattr(store, "TENDERS_PATH", tmp_path / "tenders.parquet")
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "dashboard.db")


def test_merge_and_save_first_import(tmp_path, monkeypatch):
    _isolate_store(tmp_path, monkeypatch)
    receipts_df, items_df, tenders_df = parse_json(SAMPLE_RECEIPTS_JSON)

    result = store.merge_and_save(receipts_df, items_df, tenders_df)

    assert result["receipts_added"] == 2
    assert result["items_added"] == 3
    assert result["receipts_total"] == 2

    loaded_receipts, loaded_items, _ = store.load_all()
    assert len(loaded_receipts) == 2
    assert len(loaded_items) == 3


def test_reimporting_same_file_adds_zero_new_rows(tmp_path, monkeypatch):
    _isolate_store(tmp_path, monkeypatch)
    receipts_df, items_df, tenders_df = parse_json(SAMPLE_RECEIPTS_JSON)

    store.merge_and_save(receipts_df, items_df, tenders_df)
    result = store.merge_and_save(receipts_df, items_df, tenders_df)

    assert result["receipts_added"] == 0
    assert result["items_added"] == 0
    assert result["receipts_total"] == 2
    assert result["items_total"] == 3


def test_reimporting_superset_adds_only_delta(tmp_path, monkeypatch):
    _isolate_store(tmp_path, monkeypatch)
    receipts_df, items_df, tenders_df = parse_json(SAMPLE_RECEIPTS_JSON)
    store.merge_and_save(receipts_df, items_df, tenders_df)

    superset = {
        "receipts": SAMPLE_RECEIPTS_JSON["receipts"]
        + [
            {
                **SAMPLE_RECEIPTS_JSON["receipts"][0],
                "transactionBarcode": "CCC333",
                "itemArray": [],
            }
        ]
    }
    receipts_df2, items_df2, tenders_df2 = parse_json(superset)
    result = store.merge_and_save(receipts_df2, items_df2, tenders_df2)

    assert result["receipts_added"] == 1
    assert result["receipts_total"] == 3


def test_upload_history_and_department_labels(tmp_path, monkeypatch):
    _isolate_store(tmp_path, monkeypatch)

    store.record_upload("costco-receipts.json", "json", receipts_added=2, items_added=3)
    history = store.get_upload_history()
    assert len(history) == 1
    assert history[0]["filename"] == "costco-receipts.json"

    store.set_department_label("14", "Grocery")
    labels = store.get_department_labels()
    assert labels["14"] == "Grocery"
