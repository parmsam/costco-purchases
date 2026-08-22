from dashboard.analytics.items import filter_items, top_items_by_spend
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


def test_discount_nets_onto_target_items_spend():
    _, items_df, _ = normalize_all(*parse_json(RECEIPT_WITH_DISCOUNT))
    net = items_df.set_index("item_description")["net_amount"]
    assert net["NIGHT LIGHT NIGHT LIGHT 3PK P216"] == 18.99  # 23.99 gross - 5.00 discount
    assert net["/ 1937959"] == -5.00  # the discount row's own net_amount is untouched

    top = top_items_by_spend(items_df)
    row = top[top["item_description"] == "NIGHT LIGHT NIGHT LIGHT 3PK P216"].iloc[0]
    assert row["total_spend"] == 18.99  # net, not the gross 23.99


RECEIPT_WITH_STACKED_AND_UNLABELED_DISCOUNTS = {
    "receipts": [
        {
            "membershipNumber": "111122223333",
            "transactionDate": "2026-08-15",
            "transactionBarcode": "EEE555",
            "warehouseName": "North Canton",
            "total": 14.98,
            "subTotal": 19.98,
            "taxes": 0,
            "instantSavings": 5.00,
            "totalItemCount": 1,
            "itemArray": [
                {
                    "itemNumber": "5551212",
                    "itemDescription01": "KS SNACK MIX",
                    "itemDepartmentNumber": "14",
                    "amount": 19.98,
                    "taxFlag": False,
                    "refundFlag": False,
                    "voidFlag": False,
                },
                # Stacked: instant savings, then a coupon, both on the same
                # item above. Second one uses a short non-numeric label
                # (no item number to parse out) - attribution here is
                # purely positional, so it must still net correctly.
                {
                    "itemNumber": "5551212",
                    "itemDescription01": "/ 5551212",
                    "itemDepartmentNumber": "14",
                    "amount": -3.00,
                    "taxFlag": False,
                    "refundFlag": False,
                    "voidFlag": False,
                },
                {
                    "itemNumber": "5551212",
                    "itemDescription01": "/SNAPS",
                    "itemDepartmentNumber": "14",
                    "amount": -2.00,
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


def test_items_search_table_excludes_discount_rows_and_shows_net_amount():
    receipts_df, items_df, _ = normalize_all(*parse_json(RECEIPT_WITH_DISCOUNT))
    filtered = filter_items(items_df, receipts_df)

    assert "/ 1937959" not in filtered["item_description"].values
    row = filtered[filtered["item_description"] == "NIGHT LIGHT NIGHT LIGHT 3PK P216"].iloc[0]
    assert row["net_amount"] == 18.99  # 23.99 gross - 5.00 discount, no separate discount row left


def test_stacked_and_unlabeled_discounts_both_attribute_positionally():
    _, items_df, _ = normalize_all(*parse_json(RECEIPT_WITH_STACKED_AND_UNLABELED_DISCOUNTS))
    net = items_df.set_index("item_description")["net_amount"]
    assert net["KS SNACK MIX"] == 14.98  # 19.98 - 3.00 - 2.00, both discounts attributed

    top = top_items_by_spend(items_df)
    row = top[top["item_description"] == "KS SNACK MIX"].iloc[0]
    assert row["total_spend"] == 14.98
