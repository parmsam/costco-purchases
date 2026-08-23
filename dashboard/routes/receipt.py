"""GET /receipt/{receipt_id} — a printable replica of the in-store paper receipt."""

import pandas as pd
from fasthtml.common import Div, Span, Style
from monsterui.franken import A, Button, ButtonT, Card, UkIcon

from dashboard.analytics.receipt import get_receipt
from dashboard.components import empty_state
from dashboard.data.store import load_all
from dashboard.layout import page

PRINT_STYLE = Style("""
@media print {
  .no-print { display: none !important; }
  body { background: white !important; }
}
""")


def _is_present(value) -> bool:
    return value is not None and not (isinstance(value, float) and pd.isna(value))


def _money(value) -> str:
    return f"{value:,.2f}" if _is_present(value) else ""


def _receipt_money(value) -> str:
    """Costco's own print convention: negative amounts get a trailing minus."""
    if not _is_present(value):
        return ""
    return f"{abs(value):,.2f}-" if value < 0 else f"{value:,.2f}"


def _flag(value) -> str:
    return value if value in ("Y", "N") else ""


def _pseudo_barcode_bars(value: str) -> list[int]:
    """Deterministic decorative bar widths derived from the barcode digits.

    Not a real Code128/Code39 encoding — purely a visual echo of the
    printed receipt's barcode block. The barcode number itself is printed
    as text underneath, which is the part actually worth trusting.
    """
    widths = []
    for ch in value or "":
        n = ord(ch)
        widths.append(1 + (n % 4))
        widths.append(1 + ((n * 7) % 3))
    return widths or [2, 2]


def _barcode_visual(value: str):
    bars = _pseudo_barcode_bars(value)
    bar_divs = [
        Div(style=f"width:{w * 2}px;align-self:stretch;background:{'#000' if i % 2 == 0 else 'transparent'};flex-shrink:0;")
        for i, w in enumerate(bars)
    ]
    return Div(*bar_divs, cls="flex h-14 mx-auto my-3", style="width:fit-content;")


def _item_row(item: dict):
    is_discount = item.get("is_discount")
    desc = item.get("item_description_primary") or item.get("item_description") or ""
    return Div(
        Span(item.get("item_number") or "", cls="w-16 shrink-0 text-right"),
        Span(desc, cls="flex-1 px-2 truncate" + (" italic text-neutral-500" if is_discount else "")),
        Span(_receipt_money(item.get("amount")), cls="w-16 shrink-0 text-right"),
        Span(_flag(item.get("tax_flag")), cls="w-4 shrink-0 text-right"),
        cls="flex text-xs py-0.5",
    )


def _kv_row(label: str, value: str, bold: bool = False):
    return Div(
        Span(label, cls="flex-1"),
        Span(value, cls="w-20 shrink-0 text-right"),
        cls=f"flex text-xs py-0.5 {'font-bold' if bold else ''}",
    )


def _dashed():
    return Div(cls="border-t border-dashed border-neutral-400 my-3")


def _receipt_card(receipt: dict):
    warehouse_name = receipt.get("warehouse_name") or ""
    warehouse_number = receipt.get("warehouse_number")
    store_line = f"{warehouse_name} #{warehouse_number}" if _is_present(warehouse_number) else warehouse_name

    address_lines = [
        line
        for line in (receipt.get("warehouse_address1"), receipt.get("warehouse_address2"))
        if _is_present(line)
    ]
    city_state = ", ".join(
        part for part in (receipt.get("warehouse_city"), receipt.get("warehouse_state")) if _is_present(part)
    )
    if _is_present(receipt.get("warehouse_postal_code")):
        city_state = f"{city_state} {receipt['warehouse_postal_code']}".strip()

    barcode = receipt.get("transaction_barcode") or ""
    tx_datetime = receipt.get("transaction_datetime")
    tx_date = receipt.get("transaction_date")
    when = tx_datetime if _is_present(tx_datetime) else tx_date
    when_str = f"{when:%m/%d/%Y %H:%M}" if _is_present(when) else ""

    items = receipt.get("items", [])
    tenders = receipt.get("tenders", [])

    footer_bits = [
        (label, receipt.get(field))
        for label, field in (("Whse", "warehouse_number"), ("Trm", "register_number"), ("Trn", "transaction_number"), ("Opt", "operator_number"))
        if _is_present(receipt.get(field))
    ]

    return Card(
        Div(
            Div("COSTCO", cls="text-3xl font-black tracking-tight text-center"),
            Div("WHOLESALE", cls="text-sm font-bold tracking-[0.3em] text-center border-t-2 border-b-2 border-black py-0.5 mt-0.5"),
            cls="mb-4",
        ),
        Div(store_line, cls="text-sm font-bold text-center"),
        *[Div(line, cls="text-xs text-center text-neutral-500") for line in address_lines],
        Div(city_state, cls="text-xs text-center text-neutral-500") if city_state else "",
        _barcode_visual(barcode),
        Div(barcode, cls="text-xs text-center tracking-widest text-neutral-500 mb-3"),
        Div(f"Member {receipt.get('membership_number') or ''}", cls="text-xs mb-1"),
        Div(
            *[_item_row(item) for item in items],
            cls="border-t border-neutral-300 pt-1",
        ),
        _dashed(),
        _kv_row("SUBTOTAL", _money(receipt.get("subtotal"))),
        _kv_row("TAX", _money(receipt.get("taxes"))),
        Div(
            Span("TOTAL", cls="flex-1 font-bold"),
            Span(_money(receipt.get("total")), cls="w-20 shrink-0 text-right font-bold bg-black text-white px-1 rounded"),
            cls="flex text-sm items-center py-1",
        ),
        _dashed() if tenders else "",
        *(
            [
                Div(
                    Div(f"{'*' * 12}{t['display_account_number'][-4:]}", cls="text-xs")
                    if _is_present(t.get("display_account_number"))
                    else "",
                    Div(f"Approval: {t['approval_number']}", cls="text-xs text-neutral-500")
                    if _is_present(t.get("approval_number"))
                    else "",
                    _kv_row(t.get("tender_type_name") or "TENDER", _money(t.get("amount_tender"))),
                    cls="mb-2",
                )
                for t in tenders
            ]
        ),
        _dashed(),
        _kv_row("TOTAL TAX", _money(receipt.get("taxes"))),
        _kv_row("ITEMS SOLD", str(receipt.get("total_item_count") or "")),
        _kv_row("INSTANT SAVINGS", _money(receipt.get("instant_savings")), bold=True)
        if _is_present(receipt.get("instant_savings")) and receipt.get("instant_savings")
        else "",
        Div(when_str, cls="text-xs text-center font-bold bg-black text-white rounded px-1 py-0.5 mt-2 w-fit mx-auto") if when_str else "",
        _dashed(),
        Div("Thank You!", cls="text-sm text-center font-semibold"),
        Div("Please Come Again", cls="text-sm text-center mb-3"),
        Div(
            "   ".join(f"{label}: {receipt.get(field)}" for label, field in [("Whse", "warehouse_number"), ("Trm", "register_number"), ("Trn", "transaction_number"), ("Opt", "operator_number")] if _is_present(receipt.get(field))),
            cls="text-xs text-center text-neutral-500",
        )
        if footer_bits
        else "",
        Div(cls="border-t border-dashed border-neutral-400 mt-3 mb-2"),
        Div(
            "Reconstructed from your archived purchase history — not an official Costco receipt.",
            cls="text-[10px] text-center text-neutral-400 italic leading-snug",
        ),
        # Always "white paper, black ink" regardless of the app's own
        # light/dark theme — a receipt replica shouldn't invert to white-on-
        # black just because the site is in dark mode.
        cls="max-w-sm mx-auto p-6 font-mono bg-white text-neutral-900 shadow-xl ring-1 ring-black/10",
    )


def register_receipt_routes(rt):
    @rt("/receipt/{receipt_id}")
    def get(receipt_id: str):
        receipts_df, items_df, tenders_df = load_all()
        receipt = get_receipt(receipts_df, items_df, tenders_df, receipt_id)

        if receipt is None:
            return page(
                "Receipt",
                empty_state("Receipt not found. It may have been removed or the link is stale.", icon="receipt"),
                active="",
            )

        when = receipt.get("transaction_date")
        subtitle = f"{when:%A, %B %d, %Y}" if _is_present(when) else ""

        return page(
            "Receipt",
            PRINT_STYLE,
            Div(
                A(UkIcon("arrow-left", height=16, width=16), "Back to Dashboard", href="/dashboard", cls="text-sm flex items-center gap-1.5 text-muted-foreground hover:text-primary"),
                Button(
                    UkIcon("printer", height=16, width=16),
                    "Print Receipt",
                    cls=(ButtonT.primary, "flex items-center gap-1.5"),
                    onclick="window.print()",
                ),
                cls="no-print flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 max-w-sm mx-auto",
            ),
            _receipt_card(receipt),
            active="",
            subtitle=subtitle,
        )
