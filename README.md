# 🛒 Costco Purchases

Archive your Costco in-warehouse purchase history and browse it in a local analytics dashboard.

## 1. Download your receipts

1. Log in to [costco.com](https://www.costco.com) and go to **Orders & Purchases**.
2. Open devtools (Cmd+Option+I) → **Console** tab.
3. Paste the entire contents of `downloader/costco_receipt_downloader.js` and press Enter.
4. A small panel appears in the bottom-right corner of the page. Click **Start Download**.
   - Optional: if you have a previous export, choose it in the file picker first so the new pull merges/dedups against it instead of starting fresh.
5. Once fetching finishes, click **Download JSON**, **Download CSV (both files)**, or **Download Both**. Your browser will prompt you for a save location (or fall back to your default Downloads folder).

There's no fixed folder these need to land in — the file just needs to be somewhere on disk you can find in step 2 below.

## 2. Run the dashboard

```bash
uv sync
uv run python -m dashboard.app
```

Open `http://localhost:5001`. On first run it redirects to **Upload**.

## 3. Import the data

On the **Upload** page:

- **JSON tab** — pick the JSON file you downloaded (recommended: includes payment-method data).
- **CSV tab** — pick the item-level CSV, the receipt-level CSV, or both.

Uploading reads the file in-memory and writes it into `data/` as a local cache:

- `data/receipts.parquet`, `data/items.parquet`, `data/tenders.parquet` — the analytics cache.
- `data/dashboard.db` — small SQLite metadata (upload history, custom department labels).

The original JSON/CSV file you downloaded isn't kept or referenced afterward — everything the dashboard needs lives in `data/`. `data/` is gitignored since it contains your real purchase history.

Re-uploading the same export is safe (rows are deduped); re-uploading a newer export only adds the delta.

## Tests

```bash
uv run pytest
```

## Tech stack

- **Downloader** — a single self-contained JS IIFE, pasted into devtools Console. No build step, no extension, no dependencies. Talks directly to Costco's own GraphQL endpoint (`ecom-api.costco.com/ebusiness/order/v1/orders/graphql`) using the `clientID`/`idToken` the logged-in web app already places in `localStorage`.
- **Dashboard** — Python, managed with [`uv`](https://docs.astral.sh/uv/).
  - [`python-fasthtml`](https://fastht.ml/) — routes, server, HTML-over-the-wire (including the live search on `/items` via htmx partials).
  - [MonsterUI](https://monsterui.answer.ai/) — styled components (`Card`, `NavBar`, `TableFromDicts`, tabbed upload form, etc).
  - [Plotly](https://plotly.com/python/) via `fh-plotly` — charts, rendered server-side into the page (`plotly_white` template).
  - [pandas](https://pandas.pydata.org/) — all parsing/normalization/analytics.
  - **Parquet** (via `pyarrow`) — bulk analytics cache for the three data frames (fast columnar read/concat/dedup/overwrite on each upload; no server process).
  - **SQLite** via [`fastlite`](https://github.com/AnswerDotAI/fastlite) — small mutable metadata: `upload_history`, `department_labels`.
  - `pytest` for unit tests.

No database server, no external services, no auth layer — everything runs locally against files in `data/`.

## Project layout

```
downloader/
  costco_receipt_downloader.js  # devtools console script (Part 1)
dashboard/
  app.py            # fast_app() wiring, route registration, entrypoint
  layout.py          # page shell + NavBar, MonsterUI theme headers
  components.py       # kpi_card(), section(), etc.
  charts.py           # plotly.express figure -> MonsterUI Card via fh-plotly
  data/
    schema.py          # canonical column lists/dtypes for the 3 frames
    parse_json.py       # JSON export -> (receipts_df, items_df, tenders_df)
    parse_csv.py         # item-/receipt-level CSV -> same 3 frames
    normalize.py          # reindex to canonical schema, dtype coercion, dept labeling
    store.py               # Parquet merge/dedup + SQLite metadata (fastlite)
  analytics/            # kpis, trends, items, warehouses, departments, payments
  routes/                # one module per page/route group
tests/                  # pytest — parse/normalize equivalence, dedup behavior
data/                   # gitignored — Parquet cache + SQLite db, created at runtime
```

### Data model

Three pandas DataFrames, normalized identically regardless of source format:

- **`receipts_df`** — one row per receipt, keyed by `receipt_id` (`membership_number + transaction_barcode`).
- **`items_df`** — one row per line item, FK'd to `receipt_id`.
- **`tenders_df`** — one row per payment tender, FK'd to `receipt_id`. **JSON-only** — empty when the source was CSV (the `/payments` view shows an explanatory message in that case instead of a chart).

CSV columns absent from JSON (or vice versa) are simply `NA` after `normalize.py`, so analytics code never branches on where the data came from — verified by a unit test that asserts JSON- and CSV-derived frames are equivalent for the same underlying receipts.
