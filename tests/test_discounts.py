from dashboard.analytics.items import top_items_by_spend
from dashboard.analytics.kpis import compute_kpis
from dashboard.data.normalize import normalize_all
from dashboard.data.parse_json import parse_json

RECEIPT_WITH_DISCOUNT = {
    "receipts": [
        {
            "membershipNumber": "111122223333",
            "transactionDate": "2026-08-14",
            "transactionBarcode": "DDD444",
            "warehouseName": "North Canton",
            "total": 18.99,
            "subTotal": 23.99,
            "taxes": 0,
            "instantSavings": 5.00,
            "totalItemCount": 2,
            "itemArray": [
                {
                    "itemNumber": "1937959",
                    "itemDescription01": "NIGHT LIGHT NIGHT LIGHT 3PK P216",
                    "itemDepartmentNumber": "10",
                    "amount": 23.99,
                    "taxFlag": False,
                    "refundFlag": False,
                    "voidFlag": False,
                },
                {
                    "itemNumber": "1937959",
                    "itemDescription01": "/ 1937959",
                    "itemDepartmentNumber": "10",
                    "amount": -5.00,
                    "taxFlag": False,
                    "refundFlag": False,
                    "voidFlag": False,
                },
            ],
            "couponArray": [],
            "tenderArray": [],
        }
    ]
}


def test_discount_row_is_flagged():
    _, items_df, _ = normalize_all(*parse_json(RECEIPT_WITH_DISCOUNT))
    flags = items_df.set_index("item_description")["is_discount"]
    assert bool(flags["NIGHT LIGHT NIGHT LIGHT 3PK P216"]) is False
    assert bool(flags["/ 1937959"]) is True


def test_top_items_excludes_discount_rows():
    _, items_df, _ = normalize_all(*parse_json(RECEIPT_WITH_DISCOUNT))
    top = top_items_by_spend(items_df)
    assert "/ 1937959" not in top["item_description"].values
    assert "NIGHT LIGHT NIGHT LIGHT 3PK P216" in top["item_description"].values


def test_kpi_line_item_savings_matches_receipt_level():
    receipts_df, items_df, _ = normalize_all(*parse_json(RECEIPT_WITH_DISCOUNT))
    k = compute_kpis(receipts_df, items_df)
    assert k["instant_savings_line_items"] == 5.00
    assert k["total_instant_savings"] == 5.00
