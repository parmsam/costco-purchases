"""Generate synthetic Costco purchase data for the static GitHub Pages demo.

Produces a JSON file in the same shape as the real downloader export
(matching what dashboard/data/parse_json.py expects), but entirely fake —
no real purchase data. Deterministic (seeded) so re-runs are reproducible.
"""

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

WAREHOUSES = [
    {"warehouseName": "DEMO CITY", "warehouseShortName": "DEMO CITY", "warehouseNumber": 101, "warehouseCity": "DEMO CITY", "warehouseState": "OH"},
    {"warehouseName": "SAMPLE TOWN", "warehouseShortName": "SAMPLE TOWN", "warehouseNumber": 202, "warehouseCity": "SAMPLE TOWN", "warehouseState": "OH"},
    {"warehouseName": "FIXTURE HEIGHTS", "warehouseShortName": "FIXTURE HTS", "warehouseNumber": 303, "warehouseCity": "FIXTURE HEIGHTS", "warehouseState": "PA"},
]

# (description, department, unit_price, taxable, discount_chance, discount_amount)
CATALOG = [
    ("KS ORG EGGS", "14", 6.99, "N", 0.0, 0),
    ("ROTISSERIE CHKN", "14", 4.99, "N", 0.0, 0),
    ("KS PAPER TOWELS", "22", 21.99, "Y", 0.3, 5.00),
    ("ORG BABY SPINACH", "14", 5.49, "N", 0.0, 0),
    ("KS ALMOND MILK", "14", 8.99, "N", 0.15, 2.00),
    ("KS BATH TISSUE", "22", 19.99, "Y", 0.2, 4.00),
    ("FRESH SALMON FILET", "18", 24.99, "N", 0.0, 0),
    ("KS TRAIL MIX", "12", 12.99, "N", 0.1, 3.00),
    ("GREEK YOGURT 24CT", "14", 15.49, "N", 0.0, 0),
    ("KS OLIVE OIL", "20", 17.99, "N", 0.0, 0),
    ("LAUNDRY DETERGENT", "22", 19.99, "Y", 0.25, 4.50),
    ("KS DISH SOAP 2PK", "20", 9.99, "Y", 0.0, 0),
    ("FROZEN BERRIES 4LB", "13", 11.99, "N", 0.0, 0),
    ("ROTISSERIE PIZZA", "14", 9.99, "N", 0.0, 0),
    ("KS VITAMIN D3", "17", 14.99, "N", 0.0, 0),
    ("PATIO FURNITURE SET", "38", 449.99, "Y", 0.3, 50.00),
    ("55IN LED TV", "10", 399.99, "Y", 0.4, 40.00),
    ("KS AA BATTERIES 48CT", "23", 18.99, "Y", 0.0, 0),
    ("MENS JEANS 2PK", "8", 24.99, "Y", 0.2, 5.00),
    ("KS SPARKLING WATER 35PK", "14", 8.49, "N", 0.0, 0),
    ("TIRE INSTALLATION", "44", 19.96, "Y", 0.0, 0),
    ("ALL SEASON TIRE 225/60R17", "44", 149.99, "Y", 0.0, 0),
    ("KS COLD BREW COFFEE", "14", 13.49, "N", 0.0, 0),
    ("PROTEIN BARS 20CT", "12", 16.99, "N", 0.1, 3.00),
    ("KS PAPER PLATES", "22", 14.99, "Y", 0.0, 0),
]

TENDERS = [
    ("VISA", 0.55),
    ("Debit Card", 0.25),
    ("Shop Card", 0.12),
    ("MASTERCARD", 0.08),
]


def pick_tender():
    r = random.random()
    cum = 0.0
    for name, weight in TENDERS:
        cum += weight
        if r <= cum:
            return name
    return TENDERS[0][0]


def make_receipt(rid: int, when: date) -> dict:
    wh = random.choice(WAREHOUSES)
    n_items = random.randint(2, 9)
    chosen = random.sample(CATALOG, n_items)

    item_array = []
    subtotal = 0.0
    instant_savings = 0.0
    for item_num, (desc, dept, price, tax_flag, disc_chance, disc_amt) in enumerate(chosen, start=1):
        item_array.append(
            {
                "itemNumber": str(100000 + rid * 10 + item_num),
                "itemDescription01": desc,
                "itemDescription02": None,
                "itemDepartmentNumber": dept,
                "itemUnitPriceAmount": price,
                "unit": 1,
                "amount": price,
                "taxFlag": tax_flag,
                "refundFlag": None,
                "voidFlag": None,
                "entryMethod": None,
                "fuelUnitQuantity": None,
                "fuelUomCode": None,
                "fuelGradeCode": None,
            }
        )
        subtotal += price
        if random.random() < disc_chance:
            item_array.append(
                {
                    "itemNumber": str(900000 + rid * 10 + item_num),
                    "itemDescription01": f"/ {100000 + rid * 10 + item_num}",
                    "itemDescription02": None,
                    "itemDepartmentNumber": dept,
                    "itemUnitPriceAmount": 0,
                    "unit": -1,
                    "amount": -disc_amt,
                    "taxFlag": None,
                    "refundFlag": None,
                    "voidFlag": None,
                    "entryMethod": None,
                    "fuelUnitQuantity": None,
                    "fuelUomCode": None,
                    "fuelGradeCode": None,
                }
            )
            subtotal -= disc_amt
            instant_savings += disc_amt

    taxes = round(sum(i["amount"] for i in item_array if i.get("taxFlag") == "Y") * 0.07, 2)
    total = round(subtotal + taxes, 2)
    barcode = f"{wh['warehouseNumber']}{100000 + rid:06d}{when.strftime('%y%m%d')}"

    return {
        "documentType": "WarehouseReceiptDetail",
        "receiptType": "In-Warehouse",
        "membershipNumber": "111122223333",
        "transactionType": "Sales",
        "transactionDateTime": f"{when.isoformat()}T{random.randint(9,20):02d}:{random.randint(0,59):02d}:00",
        "transactionDate": when.isoformat(),
        "warehouseShortName": wh["warehouseShortName"],
        "warehouseNumber": wh["warehouseNumber"],
        "warehouseName": wh["warehouseName"],
        "warehouseCity": wh["warehouseCity"],
        "warehouseState": wh["warehouseState"],
        "transactionBarcode": barcode,
        "totalItemCount": len(chosen),
        "instantSavings": round(instant_savings, 2),
        "subTotal": round(subtotal, 2),
        "taxes": taxes,
        "total": total,
        "registerNumber": random.randint(100, 299),
        "transactionNumber": random.randint(1, 999),
        "operatorNumber": random.randint(100, 999),
        "itemArray": item_array,
        "couponArray": [],
        "tenderArray": [{"tenderTypeName": pick_tender(), "amountTender": total, "walletType": None}],
    }


def main():
    start = date.today() - timedelta(days=365 * 2)
    end = date.today()
    span_days = (end - start).days

    n_receipts = 60
    days = sorted(random.sample(range(span_days), n_receipts))
    receipts = [make_receipt(i, start + timedelta(days=d)) for i, d in enumerate(days)]

    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo-data.json")
    out_path.write_text(json.dumps({"receipts": receipts}, indent=2))
    print(f"Wrote {len(receipts)} synthetic receipts to {out_path}")


if __name__ == "__main__":
    main()
