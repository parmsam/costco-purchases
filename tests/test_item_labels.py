from dashboard.analytics.items import distinct_items
from dashboard.data.normalize import item_label, normalize_all
from dashboard.data.parse_json import parse_json
from dashboard.data.store import get_item_labels, set_item_label
from tests.fixtures import SAMPLE_RECEIPTS_JSON


def test_item_label_defaults_to_raw_description():
    assert item_label("123456", "KS ORG EGGS", {}) == "KS ORG EGGS"
    assert item_label("123456", "KS ORG EGGS", None) == "KS ORG EGGS"


def test_item_label_uses_override_when_present():
    overrides = {"123456": "Costco Eggs"}
    assert item_label("123456", "KS ORG EGGS", overrides) == "Costco Eggs"
    assert item_label("999999", "OTHER ITEM", overrides) == "OTHER ITEM"


def test_distinct_items_one_row_per_item_number():
    _, items_df, _ = normalize_all(*parse_json(SAMPLE_RECEIPTS_JSON))
    rows = distinct_items(items_df)
    assert len(rows) == items_df["item_number"].nunique()
    assert set(rows.columns) == {"item_number", "item_description", "total_spend"}


def test_set_and_get_item_label(tmp_path, monkeypatch):
    from dashboard.data import store

    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "dashboard.db")

    set_item_label("123456", "Costco Eggs")
    assert get_item_labels()["123456"] == "Costco Eggs"

    set_item_label("123456", "")
    assert "123456" not in get_item_labels()
