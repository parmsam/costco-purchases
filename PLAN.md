# Costco Purchases: Receipt Downloader + FastHTML Analytics Dashboard

## Context

The user wants to archive their Costco in-warehouse purchase history and analyze it. Two reference projects were studied:

- **TechStud/TCRDD** (`costco_receipt_downloader.js`) — a devtools-console paste-in script. Strong points worth keeping: token validation via `localStorage` (`clientID`/`idToken`), a documented/versioned GraphQL query + canonical receipt schema, incremental merge against a previously-downloaded JSON file, per-member stats, barcode-based dedup, and a robust save flow (`showSaveFilePicker` with `<a download>` fallback).
- **harrykhh/Costco-Receipt-Downloader** — a browser extension (`content.js` + a standalone `viewer/`). Same underlying GraphQL endpoint/auth, simpler/smaller query, injects a UI card into the account page. Its main useful idea (beyond confirming the API shape) is the standalone local JSON viewer concept and the roadmap item "Export to CSV" — which we're implementing here.

This repo is currently empty. The plan below builds two deliverables from scratch:

1. A single devtools-console JS script (no extension install needed) that downloads Costco in-warehouse receipts as **JSON and/or CSV** (item-level + receipt-level).
2. A local **FastHTML** analytics dashboard (Python, `uv`-managed) that ingests either export and visualizes spending.

Both reference scripts use the same undocumented Costco endpoint (`https://ecom-api.costco.com/ebusiness/order/v1/orders/graphql`) and auth tokens already present in the logged-in user's `localStorage`. This is personal-data archiving for the account owner, run manually via their own browser devtools — same mechanism both reference projects use.

---

## Part 1 — Devtools console script (`downloader/costco_receipt_downloader.js`)

Single self-contained IIFE, paste into Console on `costco.com` while logged in and on the Orders & Purchases page (same usage flow as TCRDD).

**Reuse from TCRDD (adapt, don't copy verbatim — trim to what's needed):**
- `validateTokens()` — read `clientID`/`idToken` from `localStorage`, hard-fail with a clear message if missing.
- `LIST_RECEIPTS_QUERY` — the full GraphQL query (items, coupons, subTaxes, tenders) so the JSON export stays rich.
- `listReceipts(startDate, endDate)` — POST to the GraphQL endpoint with the same headers (`Costco.Env`, `Costco.Service`, `Costco-X-Wcs-Clientid`, `Client-Identifier`, `Costco-X-Authorization`).
- `getExistingReceipts()` — on-page buttons to either load a previously-downloaded JSON file (to merge/dedup incrementally) or start fresh.
- Canonical normalize + merge/dedup logic keyed on `membershipNumber + transactionBarcode` (drop the versioned-schema-changelog ceremony from TCRDD — it's overkill for a single-user personal script; keep just the dedup/merge behavior).
- 3-year max date range calculation, per-member stats logging.
- Save flow: `showSaveFilePicker` first, `<a download>` blob fallback second.

**New work (not in either reference):**
- **CSV export functions**, hand-written (no library available in a bare console context):
  - `toItemLevelCSV(receipts)` — one row per line item: receipt fields (`transactionDate`, `warehouseName`, `warehouseShortName`, `warehouseCity`, `warehouseState`, `membershipNumber`, `transactionBarcode`, `total`, `subTotal`, `taxes`, `instantSavings`) repeated, plus item fields (`itemNumber`, `itemDescription01`, `itemDescription02`, `itemDepartmentNumber`, `itemUnitPriceAmount`, `unit`, `amount`, `taxFlag`, `refundFlag`, `voidFlag`, `entryMethod`).
  - `toReceiptLevelCSV(receipts)` — one row per receipt, no items: the receipt-level fields above plus `totalItemCount`.
  - A small `csvEscape(value)` helper (quote if the field contains `,`, `"`, or a newline; double up internal quotes) — this is the one piece of real new logic, since neither reference does CSV at all.
- **On-page format picker**: replace TCRDD's single implicit "download JSON" step with three buttons after fetch completes — "Download JSON", "Download CSV (both files)", "Download Both" — reusing the existing button-injection pattern from `getExistingReceipts()`.
- Drop everything specific to the browser-extension packaging (manifest.json, content.js injection into the live page, `styles.css`) — not applicable to a console-paste script.

**Verification**: paste into Console on a real logged-in Costco session, confirm JSON download matches previous TCRDD-style output shape, confirm the two CSVs open cleanly in a spreadsheet app with correct column alignment and no broken quoting on descriptions containing commas.

---

## Part 2 — FastHTML analytics dashboard (`dashboard/`)

Python app using `python-fasthtml` + `MonsterUI` (polished components), `uv` for packaging, Plotly for charts (via the `fh-plotly` helper, with a documented manual `NotStr(fig.to_html())` fallback if that package proves unreliable at build time).

### Project layout

```
costco-purchases/
├── pyproject.toml              # uv-managed; fasthtml, monsterui, fh-plotly, pandas, pyarrow, fastlite
├── downloader/
│   └── costco_receipt_downloader.js
├── data/                        # gitignored — Parquet cache + SQLite metadata db, created at runtime
├── dashboard/
│   ├── app.py                   # fast_app() + hdrs (MonsterUI Theme + plotly_headers) + serve()
│   ├── layout.py                # shared page shell + NavBar
│   ├── data/
│   │   ├── schema.py             # canonical column lists/dtypes for receipts/items/tenders
│   │   ├── parse_json.py         # JSON export -> (receipts_df, items_df, tenders_df)
│   │   ├── parse_csv.py          # item-level + receipt-level CSV -> same 3 frames
│   │   ├── normalize.py          # reindex to canonical schema, dtype coercion, dept labeling
│   │   └── store.py              # Parquet load/merge/dedup + SQLite (fastlite) metadata
│   ├── analytics/                # kpis.py, trends.py, items.py, warehouses.py, departments.py, payments.py
│   ├── charts.py                 # plotly.express figure -> plotly2fasthtml(fig)
│   ├── components.py             # kpi_card(), filter_bar(), etc (MonsterUI wrappers)
│   └── routes/                   # upload.py, overview.py, trends.py, items.py, warehouses.py, departments.py, payments.py
└── .gitignore                    # data/ (contains real purchase history — never commit)
```

### Data model

Three pandas DataFrames, normalized identically regardless of source format:
- **`receipts_df`**: `receipt_id` (`membership_number + transaction_barcode`, PK), date/warehouse/membership fields, `total`, `subtotal`, `taxes`, `instant_savings`, `total_item_count`, `source` (`"json"`/`"csv"`).
- **`items_df`**: `receipt_id` FK, `line_no` (positional, since `item_number` isn't unique per receipt), description, `item_department_number`, `amount`, `unit_price`, `tax_flag`/`refund_flag`/`void_flag`, fuel fields (nullable).
- **`tenders_df`**: `receipt_id` FK, `tender_type_name`, `amount_tender`, `wallet_type` — **JSON-only**; empty when the source was CSV. Views using this must handle the empty case explicitly (e.g. the Payments view shows an explanatory alert instead of a broken chart).

`itemDepartmentNumber` is a raw Costco code with no reliable public name mapping — surface it as `Dept #NNNN`, not a fabricated category name. `couponArray` folds into an optional `coupon_amount` column on `items_df` rather than becoming a 4th table; `subTaxes` is dropped (not useful for analytics).

CSV ingestion: prefer the receipt-level CSV as authoritative for `receipts_df` when present (covers edge cases like all-void receipts); derive it from `items_df.groupby(receipt_id).first()` only if the item-level CSV is the sole input. Columns absent from CSV (vs. JSON) are filled via `reindex(columns=canonical, fill_value=pd.NA)` in `normalize.py` so downstream code never branches on source format.

### Persistence — Parquet + SQLite (per user's confirmed decision)

- **Parquet** (`data/receipts.parquet`, `items.parquet`, `tenders.parquet`) is the bulk analytics cache: on upload, load existing + new, `pd.concat`, dedup (`receipt_id` for receipts, `(receipt_id, line_no)` for items, `(receipt_id, tender_type_name, amount_tender)` for tenders, `keep='last'` so re-imports can correct stale data), overwrite. Simple and fast at personal-purchase-history scale.
- **SQLite** (`data/dashboard.db`, via `fastlite`/`database()` — FastHTML's native persistence idiom) holds two small mutable tables:
  - `upload_history`: filename, timestamp, format, receipts_added, items_added — shown on the dashboard as "last imported: ...".
  - `department_labels`: `dept_number -> custom_label`, user-editable override for the generated `Dept #NNNN` default (small settings-style table, not bulk data — a natural SQLite fit, not Parquet).

### Upload flow

`GET /` redirects to `/dashboard` if the Parquet cache is non-empty, else `/upload`. `GET /upload` shows a MonsterUI-tabbed form (JSON tab: one file input; CSV tab: two file inputs — item-level + receipt-level). `POST /upload` reads files in-memory (`io.BytesIO`), dispatches to `parse_json.py`/`parse_csv.py` → `normalize.py` → `store.merge_and_save()`, records an `upload_history` row, and redirects to `/dashboard` with a flash message showing new-vs-total counts.

### Dashboard views

- `/dashboard` — KPI cards (total spend, receipt count, date range, avg basket, total instant savings, avg items/receipt) + one monthly-spend trend chart + recent-receipts mini-table.
- `/trends` — monthly spend bar chart, month-over-month table, year-over-year comparison if data spans multiple years.
- `/items` — searchable/filterable/paginated itemized transaction table (htmx partial at `/items/table` for live filtering) + top-items-by-spend and top-items-by-frequency tables.
- `/warehouses` — spend by warehouse (chart + table: visits, avg basket).
- `/departments` — spend by `Dept #NNNN` (chart + table), with sample item descriptions per department as an inline hint, and respecting any `department_labels` override from SQLite.
- `/payments` — payment-method breakdown chart; explanatory MonsterUI `Alert` in place of the chart when `tenders_df` is empty (CSV-only import).

Excluded from v1 (flagged as realistic scope-cuts, not oversights): fuel-specific analytics, a standalone coupon view, auth/multi-tenancy, forecasting.

### Charting

`plotly.express` figures rendered via `fh-plotly`'s `plotly2fasthtml()`, with `plotly_headers` loaded once in `fast_app(hdrs=...)` alongside the MonsterUI theme headers. Charts use the `plotly_white` template placed inside MonsterUI `Card`s so they stay readable in both light/dark mode without building full theme-sync (flagged as a known v1 limitation, not a blocker).

### Build order

1. `pyproject.toml` + `uv sync` — confirm `fasthtml`, `monsterui`, `fh-plotly`, `pandas`, `pyarrow`, `fastlite` install cleanly.
2. `dashboard/data/schema.py`, `parse_json.py`, `parse_csv.py`, `normalize.py` + unit tests confirming JSON and CSV of the same underlying data normalize to equivalent frames.
3. `dashboard/data/store.py` (Parquet merge/dedup + SQLite metadata) + a dedup unit test (re-importing the same file adds zero new rows).
4. `dashboard/app.py`, `layout.py`, `routes/upload.py` — get upload → cache → redirect working end-to-end with a small hand-built sample JSON fixture (no real Costco data needed for this step).
5. `dashboard/charts.py`, `analytics/*.py`, remaining `routes/*.py` — build views one at a time, KPI/trends first (highest value), items/warehouses/departments/payments after.

### Parallelization

Mapped onto the 7 tracked tasks:

- **#1 (JS downloader script)** and **#2 (Python scaffolding)** touch disjoint files (`downloader/` vs. `pyproject.toml`/`dashboard/` dirs) and share no dependency — safe to run in parallel, and the only pair that is.
- **#3–#7 are a strict sequential chain**, each consuming the previous step's output: #3 (schema/parse/normalize) needs #2's project structure; #4 (store.py) needs #3's schema; #5 (app/layout/upload route) needs #2–#4 wired together; #6 (charts/analytics/views) needs #4's store and #5's app shell; #7 (end-to-end verification) needs everything built.
- Net effect: parallelism only helps at the very start (#1 + #2 together); from #3 onward, work one task at a time in numeric order.

### Verification

- Unit tests (`tests/`) for parse/normalize/dedup as noted above, run via `uv run pytest`.
- Manual end-to-end: run the console script against a real logged-in session (or use previously-archived data if the user already has some), download both JSON and CSV, upload each independently into the dashboard via `uv run python -m dashboard.app`, and confirm both produce the same KPI numbers on `/dashboard` (validates the JSON/CSV normalization-equivalence goal). Confirm re-uploading the same file doesn't duplicate rows, and re-uploading a superset file adds only the delta.
- Visually check `/items` filtering (htmx partial updates without full page reload) and the `/payments` empty-state alert when only CSV data is loaded.

### Critical files

- `downloader/costco_receipt_downloader.js`
- `dashboard/app.py`
- `dashboard/data/normalize.py`
- `dashboard/data/store.py`
- `dashboard/routes/upload.py`
- `dashboard/charts.py`
- `pyproject.toml`
