"""Shared sample data for parse/normalize/store tests."""

SAMPLE_RECEIPTS_JSON = {
    "exportedAt": "2026-08-01T00:00:00.000Z",
    "receipts": [
        {
            "warehouseName": "Canton",
            "warehouseShortName": "Canton",
            "warehouseCity": "Canton",
            "warehouseState": "OH",
            "membershipNumber": "111122223333",
            "transactionDate": "2026-06-15",
            "transactionBarcode": "AAA111",
            "total": 152.34,
            "subTotal": 140.00,
            "taxes": 12.34,
            "instantSavings": 5.00,
            "totalItemCount": 2,
            "itemArray": [
                {
                    "itemNumber": "123456",
                    "itemDescription01": "KS ORG EGGS",
                    "itemDescription02": None,
                    "itemDepartmentNumber": "14",
                    "itemUnitPriceAmount": 6.99,
                    "unit": "1",
                    "amount": 6.99,
                    "taxFlag": False,
                    "refundFlag": False,
                    "voidFlag": False,
                    "entryMethod": "T",
                    "couponArray": [],
                },
                {
                    "itemNumber": "789012",
                    "itemDescription01": "ROTISSERIE CHKN",
                    "itemDescription02": None,
                    "itemDepartmentNumber": "14",
                    "itemUnitPriceAmount": 4.99,
                    "unit": "1",
                    "amount": 4.99,
                    "taxFlag": False,
                    "refundFlag": False,
                    "voidFlag": False,
                    "entryMethod": "T",
                    "couponArray": [],
                },
            ],
            "subTaxes": [],
            "tenderArray": [
                {"tenderTypeName": "VISA", "amountTender": 152.34, "walletType": None}
            ],
        },
        {
            "warehouseName": "Canton",
            "warehouseShortName": "Canton",
            "warehouseCity": "Canton",
            "warehouseState": "OH",
            "membershipNumber": "111122223333",
            "transactionDate": "2026-07-01",
            "transactionBarcode": "BBB222",
            "total": 89.50,
            "subTotal": 85.00,
            "taxes": 4.50,
            "instantSavings": 0,
            "totalItemCount": 1,
            "itemArray": [
                {
                    "itemNumber": "555555",
                    "itemDescription01": "PAPER TOWELS",
                    "itemDescription02": None,
                    "itemDepartmentNumber": "22",
                    "itemUnitPriceAmount": 85.00,
                    "unit": "1",
                    "amount": 85.00,
                    "taxFlag": True,
                    "refundFlag": False,
                    "voidFlag": False,
                    "entryMethod": "T",
                    "couponArray": [],
                }
            ],
            "subTaxes": [],
            "tenderArray": [
                {"tenderTypeName": "DEBIT", "amountTender": 89.50, "walletType": None}
            ],
        },
    ],
}

# Same two receipts, as they'd appear in the item-level and receipt-level CSVs.
SAMPLE_ITEM_CSV = """transactionDate,warehouseName,warehouseShortName,warehouseCity,warehouseState,membershipNumber,transactionBarcode,total,subTotal,taxes,instantSavings,itemNumber,itemDescription01,itemDescription02,itemDepartmentNumber,itemUnitPriceAmount,unit,amount,taxFlag,refundFlag,voidFlag,entryMethod
2026-06-15,Canton,Canton,Canton,OH,111122223333,AAA111,152.34,140.00,12.34,5.00,123456,KS ORG EGGS,,14,6.99,1,6.99,False,False,False,T
2026-06-15,Canton,Canton,Canton,OH,111122223333,AAA111,152.34,140.00,12.34,5.00,789012,ROTISSERIE CHKN,,14,4.99,1,4.99,False,False,False,T
2026-07-01,Canton,Canton,Canton,OH,111122223333,BBB222,89.50,85.00,4.50,0,555555,PAPER TOWELS,,22,85.00,1,85.00,True,False,False,T
"""

SAMPLE_RECEIPT_CSV = """transactionDate,warehouseName,warehouseShortName,warehouseCity,warehouseState,membershipNumber,transactionBarcode,total,subTotal,taxes,instantSavings,totalItemCount
2026-06-15,Canton,Canton,Canton,OH,111122223333,AAA111,152.34,140.00,12.34,5.00,2
2026-07-01,Canton,Canton,Canton,OH,111122223333,BBB222,89.50,85.00,4.50,0,1
"""
