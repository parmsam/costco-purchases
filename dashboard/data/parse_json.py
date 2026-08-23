"""Parse a costco_receipt_downloader.js JSON export into normalized frames."""

import pandas as pd

from dashboard.data.schema import ITEMS_COLUMNS, RECEIPTS_COLUMNS, TENDERS_COLUMNS, empty_frame


def _receipt_id(receipt: dict) -> str:
    return f"{receipt.get('membershipNumber')}__{receipt.get('transactionBarcode')}"


def parse_json(data: dict | list) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Parse the downloader's JSON export.

    Accepts either the full export object (``{"receipts": [...]}``) or a
    bare list of receipts, for flexibility with hand-built fixtures.
    """
    receipts = data.get("receipts", []) if isinstance(data, dict) else data

    receipt_rows = []
    item_rows = []
    tender_rows = []

    for receipt in receipts:
        rid = _receipt_id(receipt)

        receipt_rows.append(
            {
                "receipt_id": rid,
                "membership_number": receipt.get("membershipNumber"),
                "transaction_barcode": receipt.get("transactionBarcode"),
                "transaction_date": receipt.get("transactionDate"),
                "transaction_datetime": receipt.get("transactionDateTime"),
                "warehouse_name": receipt.get("warehouseName"),
                "warehouse_short_name": receipt.get("warehouseShortName"),
                "warehouse_number": receipt.get("warehouseNumber"),
                "warehouse_city": receipt.get("warehouseCity"),
                "warehouse_state": receipt.get("warehouseState"),
                "warehouse_address1": receipt.get("warehouseAddress1"),
                "warehouse_address2": receipt.get("warehouseAddress2"),
                "warehouse_postal_code": receipt.get("warehousePostalCode"),
                "total": receipt.get("total"),
                "subtotal": receipt.get("subTotal"),
                "taxes": receipt.get("taxes"),
                "instant_savings": receipt.get("instantSavings"),
                "total_item_count": receipt.get("totalItemCount"),
                "register_number": receipt.get("registerNumber"),
                "transaction_number": receipt.get("transactionNumber"),
                "operator_number": receipt.get("operatorNumber"),
                "source": "json",
            }
        )

        # couponArray is receipt-level (not nested per item), with each coupon
        # linked back to an item via associatedItemNumber. itemNumber isn't
        # guaranteed unique per receipt, so assign each coupon's total to only
        # the first matching item row to avoid double-counting.
        coupon_totals_by_item_number = {}
        for c in receipt.get("couponArray") or []:
            item_num = c.get("associatedItemNumber")
            coupon_totals_by_item_number[item_num] = coupon_totals_by_item_number.get(
                item_num, 0
            ) + (c.get("amountCoupon") or 0)
        assigned_item_numbers = set()

        for line_no, item in enumerate(receipt.get("itemArray") or []):
            item_num = item.get("itemNumber")
            coupon_amount = None
            if item_num in coupon_totals_by_item_number and item_num not in assigned_item_numbers:
                coupon_amount = coupon_totals_by_item_number[item_num]
                assigned_item_numbers.add(item_num)
            item_rows.append(
                {
                    "receipt_id": rid,
                    "line_no": line_no,
                    "item_number": item.get("itemNumber"),
                    "item_description": " ".join(
                        part
                        for part in (item.get("itemDescription01"), item.get("itemDescription02"))
                        if part
                    ).strip()
                    or None,
                    "item_description_primary": item.get("itemDescription01"),
                    "item_department_number": item.get("itemDepartmentNumber"),
                    "amount": item.get("amount"),
                    "unit_price": item.get("itemUnitPriceAmount"),
                    "unit": item.get("unit"),
                    "tax_flag": item.get("taxFlag"),
                    "refund_flag": item.get("refundFlag"),
                    "void_flag": item.get("voidFlag"),
                    "entry_method": item.get("entryMethod"),
                    "coupon_amount": coupon_amount or None,
                    "fuel_unit_quantity": item.get("fuelUnitQuantity"),
                    "fuel_grade_code": item.get("fuelGradeCode"),
                    "fuel_uom_code": item.get("fuelUomCode"),
                }
            )

        for tender in receipt.get("tenderArray") or []:
            tender_rows.append(
                {
                    "receipt_id": rid,
                    "tender_type_name": tender.get("tenderTypeName"),
                    "amount_tender": tender.get("amountTender"),
                    "wallet_type": tender.get("walletType"),
                    "display_account_number": tender.get("displayAccountNumber"),
                    "approval_number": tender.get("approvalNumber"),
                    "entry_method": tender.get("entryMethod"),
                }
            )

    receipts_df = pd.DataFrame(receipt_rows) if receipt_rows else empty_frame(RECEIPTS_COLUMNS)
    items_df = pd.DataFrame(item_rows) if item_rows else empty_frame(ITEMS_COLUMNS)
    tenders_df = pd.DataFrame(tender_rows) if tender_rows else empty_frame(TENDERS_COLUMNS)

    return receipts_df, items_df, tenders_df
