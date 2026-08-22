# 🛒 Costco Purchases

Archive your Costco in-warehouse purchase history and browse it in a local analytics dashboard — spending trends, top items, warehouse breakdowns, payment methods, and a printable copy of any past receipt.

Everything runs **on your own computer**. Nothing is uploaded anywhere, and no account or sign-up is needed beyond your existing Costco login.

---

## Try it without installing anything

Two hosted options if you just want to look before you install anything locally:

- **[Static demo](https://parmsam.github.io/costco-purchases/)** — pre-loaded sample data, browse-only, no upload. Good for seeing what the dashboard looks like.
- **[Live demo](https://costco-purchases.vercel.app)** — the real app, upload your own export and click around it for real. Runs on Vercel with a deliberately different storage model from the local version: your data lives only in server memory for that visit, scoped to you (other visitors can't see it), and a re-upload replaces it rather than merging like the local version does. Nothing ever touches disk, and it disappears once your session goes idle — treat it as a place to try the tool, not to keep your purchase history. For that, run it locally (below).

---

## 🐣 New here? Start here (no coding experience needed)

This walks through the whole thing from a blank computer — about 15 minutes, all copy-and-paste. It assumes nothing except that you can log in to costco.com and open a program called **Terminal** (Mac) or the app store **Windows Terminal** (Windows).

### What you'll need

- A Mac, or a Windows/Linux computer.
- A Costco.com account with some in-warehouse purchase history.
- 15 minutes.

### Step 0 — Open a terminal

A **terminal** is just a window where you type commands instead of clicking. You'll only need it briefly, and every command below is meant to be copy-pasted exactly as written.

- **Mac**: press `Cmd + Space`, type `Terminal`, press Enter.
- **Windows**: press the Windows key, type `Terminal`, press Enter.

### Step 1 — Install `uv` (one-time setup)

`uv` is the tool this project uses to install Python and its dependencies automatically — you don't need to install Python yourself.

Paste **one** of these into your terminal and press Enter:

```bash
# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If it worked, you'll see some install output and your prompt returns. (Full install docs: [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).)

### Step 2 — Get this project onto your computer

If you don't already have it, download it as a ZIP: on the [GitHub page for this project](https://github.com/parmsam/costco-purchases), click the green **Code** button → **Download ZIP**, then unzip it (double-click it on Mac; right-click → Extract All on Windows).

In your terminal, move into that folder — replace the path below with wherever you unzipped it:

```bash
cd path/to/costco-purchases
```

Tip: on Mac, you can type `cd ` (with a trailing space) and then drag the unzipped folder from Finder straight into the terminal window — it fills in the path for you.

### Step 3 — Get your Costco purchase history

Costco doesn't offer a normal "export my data" button, so this project includes a small script that runs *inside your own browser, while you're logged in* — it never sends your login anywhere else.

1. Log in to [costco.com](https://www.costco.com) and go to **Orders & Purchases**.
2. Open your browser's **developer tools**: press `Cmd+Option+I` (Mac) or `F12` (Windows), then click the **Console** tab at the top of the panel that opens. (This is a normal, built-in browser feature — no extension needed.)
3. Open the file `downloader/costco_receipt_downloader.js` from the project folder you downloaded (any text editor, or double-click it), select all the text, and copy it.
4. Click into the Console tab, paste, and press Enter.
5. A small panel appears in the bottom-right corner of the Costco page. Click **Start Fresh (No File)**.
6. Once it finishes, click **Download JSON**. Your browser will save a file (usually to your Downloads folder) — remember where it lands, you'll pick it in Step 5.

### Step 4 — Start the dashboard

Back in your terminal (still inside the `costco-purchases` folder from Step 2), run:

```bash
uv sync
uv run python -m dashboard.app
```

The first command installs everything the dashboard needs (only needed once). The second starts it — leave this terminal window open while you use the dashboard.

### Step 5 — Open it and upload your data

Open your web browser and go to **http://localhost:5001**

It'll land on an **Upload** page. Click the **JSON** tab, choose the file you downloaded in Step 3, and click **Upload JSON**. You'll land on your Dashboard.

That's it — from now on, whenever you want to reopen it, just re-run the `uv run python -m dashboard.app` command from Step 4 in a terminal and revisit the same page in your browser. To add newer purchases later, re-run the browser script from Step 3 and upload again — old data is never lost, only added to (see [Why re-uploads merge instead of replace](#why-re-uploads-merge-instead-of-replace)).

### Troubleshooting

| Problem | What to try |
|---|---|
| `command not found: uv` after Step 1 | Close and reopen your terminal window, then try `uv sync` again — the install needs a fresh terminal to take effect. |
| Browser tab is blank / "can't reach this page" | Make sure the terminal from Step 4 is still open and didn't show an error. |
| `Address already in use` when starting | Something's already using that port — close any other terminal windows running this project, or restart your computer. |
| The devtools script shows a red error about missing tokens | Make sure you're logged in to costco.com in that same browser tab before pasting the script. |
| Nothing happens after pasting the script | Make sure you copied the *entire* file, from the very first line to the very last. |

---

## For developers

The rest of this README assumes familiarity with the command line, git, and Python.

### 1. Download your receipts

1. Log in to [costco.com](https://www.costco.com) and go to **Orders & Purchases**.
2. Open devtools (Cmd+Option+I) → **Console** tab.
3. Paste the entire contents of `downloader/costco_receipt_downloader.js` and press Enter.
4. A small panel appears in the bottom-right corner of the page. Click **Start Download**.
   - Optional: if you have a previous export, choose it in the file picker first so the new pull merges/dedups against it instead of starting fresh.
5. Once fetching finishes, click **Download JSON**, **Download CSV (both files)**, or **Download Both**. Your browser will prompt you for a save location (or fall back to your default Downloads folder).

There's no fixed folder these need to land in — the file just needs to be somewhere on disk you can find in step 2 below.

### 2. Run the dashboard

```bash
uv sync
uv run python -m dashboard.app
```

Open `http://localhost:5001`. On first run it redirects to **Upload**.

### 3. Import the data

On the **Upload** page:

- **JSON tab** — pick the JSON file you downloaded (recommended: includes payment-method data).
- **CSV tab** — pick the item-level CSV, the receipt-level CSV, or both.

Uploading reads the file in-memory and writes it into `data/` as a local cache:

- `data/receipts.parquet`, `data/items.parquet`, `data/tenders.parquet` — the analytics cache.
- `data/dashboard.db` — small SQLite metadata (upload history, custom department/item labels).

The original JSON/CSV file you downloaded isn't kept or referenced afterward — everything the dashboard needs lives in `data/`. `data/` is gitignored since it contains your real purchase history.

Re-uploading the same export is safe (rows are deduped); re-uploading a newer export only adds the delta.

#### Why re-uploads merge instead of replace

Each upload is merged into the existing Parquet store, not swapped in for it: old and new rows are combined, then deduped by a stable key (`receipt_id` for receipts, `receipt_id + line_no` for items, `receipt_id + tender_type_name + amount_tender` for tenders), keeping the newer version whenever a row exists in both.

This matters because the downloader always re-fetches Costco's full ~3-year lookback window from scratch on every run — it isn't incremental. A receipt older than 3 years is simply absent from a fresh download. If uploads replaced the store instead of merging, every re-upload would silently drop whatever had aged out of that window. Because they merge, a receipt stays in your local store permanently once captured, even after Costco's own API has forgotten it.

### Tests

```bash
uv run pytest
```

### Tech stack

- **Downloader** — a single self-contained JS IIFE, pasted into devtools Console. No build step, no extension, no dependencies. Talks directly to Costco's own GraphQL endpoint (`ecom-api.costco.com/ebusiness/order/v1/orders/graphql`) using the `clientID`/`idToken` the logged-in web app already places in `localStorage`.
- **Dashboard** — Python, managed with [`uv`](https://docs.astral.sh/uv/).
  - [`python-fasthtml`](https://fastht.ml/) — routes, server, HTML-over-the-wire (including the live search on `/items` via htmx partials).
  - [MonsterUI](https://monsterui.answer.ai/) — styled components (`Card`, `NavBar`, `TableFromDicts`, tabbed upload form, etc).
  - [Plotly](https://plotly.com/python/) via `fh-plotly` — charts, rendered server-side into the page (`plotly_white` template).
  - [pandas](https://pandas.pydata.org/) — all parsing/normalization/analytics.
  - **Parquet** (via `pyarrow`) — bulk analytics cache for the three data frames (fast columnar read/concat/dedup/overwrite on each upload; no server process).
  - **SQLite** via [`fastlite`](https://github.com/AnswerDotAI/fastlite) — small mutable metadata: `upload_history`, `department_labels`, `item_labels`.
  - `pytest` for unit tests.

No database server, no external services, no auth layer — everything runs locally against files in `data/`.

### Project layout

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
    normalize.py          # reindex to canonical schema, dtype coercion, dept/item labeling
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
