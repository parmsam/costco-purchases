"""Upload flow: GET /upload shows the form, POST /upload ingests a file."""

import json

from fasthtml.common import Div, Form, P, RedirectResponse, UploadFile
from monsterui.franken import (
    A,
    Button,
    ButtonT,
    Card,
    CardBody,
    DivLAligned,
    H4,
    LabelInput,
    TabContainer,
    UkIcon,
)

from dashboard.data.normalize import normalize_all
from dashboard.data.parse_csv import parse_csv
from dashboard.data.parse_json import parse_json
from dashboard.data.store import merge_and_save, record_upload
from dashboard.layout import page


def _upload_page(flash: str | None = None):
    json_tab = Div(
        Form(
            LabelInput("JSON export", type="file", name="json_file", accept="application/json"),
            Button("Upload JSON", cls=ButtonT.primary, type="submit"),
            action="/upload/json",
            method="post",
            enctype="multipart/form-data",
            cls="space-y-4",
        ),
        cls="pt-4",
    )
    csv_tab = Div(
        Form(
            LabelInput("Item-level CSV", type="file", name="item_csv", accept=".csv"),
            LabelInput(
                "Receipt-level CSV (optional but recommended)",
                type="file",
                name="receipt_csv",
                accept=".csv",
            ),
            Button("Upload CSV", cls=ButtonT.primary, type="submit"),
            action="/upload/csv",
            method="post",
            enctype="multipart/form-data",
            cls="space-y-4",
        ),
        cls="pt-4",
    )

    downloader_link = A(
        "downloader/costco_receipt_downloader.js",
        href="https://github.com/parmsam/costco-purchases/blob/main/downloader/costco_receipt_downloader.js",
        target="_blank",
        rel="noopener noreferrer",
        cls="underline text-primary",
    )
    step_contents = [
        "Log in to costco.com and open Orders & Purchases.",
        P("Paste ", downloader_link, " into the browser console.", cls="text-sm text-muted-foreground"),
        "Download the JSON (recommended) or CSV export.",
        "Upload it below.",
    ]
    steps = Div(
        *[
            DivLAligned(
                Div(str(n), cls="shrink-0 grid place-items-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold"),
                P(content, cls="text-sm text-muted-foreground") if isinstance(content, str) else content,
                cls="gap-3 items-center",
            )
            for n, content in enumerate(step_contents, start=1)
        ],
        cls="space-y-2.5 mb-6",
    )

    return page(
        "Upload",
        Card(
            CardBody(
                DivLAligned(
                    UkIcon("upload", height=20, width=20, cls="text-primary"),
                    H4("Import your Costco purchase history"),
                    cls="gap-2 mb-4",
                ),
                steps,
                Div(
                    DivLAligned(
                        UkIcon("check-circle-2", height=16, width=16, cls="text-primary shrink-0"),
                        P(flash, cls="text-sm font-semibold"),
                        cls="gap-2",
                    ),
                    cls="mb-4 p-3 rounded-lg bg-primary/5",
                )
                if flash
                else "",
                TabContainer(
                    ("JSON", json_tab),
                    ("CSV", csv_tab),
                ),
            ),
            cls="max-w-2xl",
        ),
        active="/upload",
        subtitle="Bring in a fresh export, or merge in new receipts",
    )


def register_upload_routes(rt):
    @rt("/upload")
    def get():
        return _upload_page()

    @rt("/upload/json")
    async def post(json_file: UploadFile):
        contents = await json_file.read()
        data = json.loads(contents)
        receipts_df, items_df, tenders_df = normalize_all(*parse_json(data))
        result = merge_and_save(receipts_df, items_df, tenders_df)
        record_upload(
            json_file.filename,
            "json",
            result["receipts_added"],
            result["items_added"],
        )
        return RedirectResponse("/dashboard", status_code=303)

    @rt("/upload/csv")
    async def post(item_csv: UploadFile = None, receipt_csv: UploadFile = None):
        item_bytes = await item_csv.read() if item_csv and item_csv.filename else None
        receipt_bytes = await receipt_csv.read() if receipt_csv and receipt_csv.filename else None
        if item_bytes is None and receipt_bytes is None:
            return _upload_page(flash="Please choose at least one CSV file.")

        receipts_df, items_df, tenders_df = normalize_all(
            *parse_csv(item_csv=item_bytes, receipt_csv=receipt_bytes)
        )
        result = merge_and_save(receipts_df, items_df, tenders_df)
        filename = (item_csv.filename if item_bytes else None) or (
            receipt_csv.filename if receipt_bytes else None
        )
        record_upload(filename, "csv", result["receipts_added"], result["items_added"])
        return RedirectResponse("/dashboard", status_code=303)
