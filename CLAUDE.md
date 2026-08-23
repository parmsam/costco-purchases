# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                          # install/update dependencies
uv run python -m dashboard.app   # run the local dashboard (always port 5001, hardcoded in app.py)
uv run pytest                    # run the test suite
node --check downloader/costco_receipt_downloader.js  # syntax-check the standalone JS (no pytest coverage for it)
```

Deploy the live demo: `vercel --prod --yes` from the repo root (requires `vercel login` once; no `vercel.json` needed — Vercel auto-detects `main.py`/`pyproject.toml`).

## Storage backend switch

`dashboard/data/store.py` picks its backend at import time based on environment, not a config file:
- Default (local dev, tests): disk-backed — Parquet + SQLite under `data/`, merges/dedups on upload, persists across runs.
- `VERCEL` or `DASHBOARD_EPHEMERAL` set: routes to `dashboard/data/_memory_store.py` — in-memory, per-visitor (keyed by a session id stamped into the FastHTML cookie via `assign_session` in `app.py`), **replaces** rather than merges on re-upload, nothing touches disk. Vercel sets `VERCEL=1` automatically; set `DASHBOARD_EPHEMERAL=1` to exercise this path locally (e.g. for regenerating the GitHub Pages demo without touching real data).

Every function in `store.py` has an `if EPHEMERAL: return _memory_store.X(...)` guard at the top; the disk code below it is the original, untouched logic — keep that pattern when adding new store functions.

## Two demo surfaces — not auto-synced

- **Vercel** (`https://costco-purchases.vercel.app`) — the live app, ephemeral backend, always current after a deploy.
- **GitHub Pages** (`docs/`, served from `main`/`/docs`) — a **static, pre-rendered snapshot**, not live. It does NOT rebuild when app code changes. Regenerate it after any change that affects rendered HTML (new UI, changed numbers/behavior):
  1. `uv run python scripts/generate_demo_data.py <path>.json` — synthetic sample data.
  2. Run the app with `DASHBOARD_EPHEMERAL=1` (keeps this out of real `data/`), upload that JSON via `/upload/json`, `curl` each page (`dashboard`, `trends`, `items`, `warehouses`, `departments`, `payments`, `upload`, one `/receipt/{id}`) into a raw-dir using one shared cookie jar (session-scoped).
  3. `uv run python scripts/build_demo_site.py --raw-dir <raw-dir> --out-dir docs` — rewrites links, disables backend-only bits, injects the static-demo banner.
  4. Commit `docs/`.

## Gotchas

- `.vercelignore`'s `data/` entry must stay anchored as `/data/` — an unanchored `data/` pattern also matches `dashboard/data/` (the actual Python package containing `store.py`) and breaks the deploy with `ModuleNotFoundError: dashboard.data`. Already hit this once.
- `data/` (repo root, gitignored) holds **real personal purchase data** — parquet + sqlite, created at runtime. Don't delete or overwrite it casually; disk-mode uploads merge/dedup into it rather than replace.
- `.reference/` (gitignored) holds a downloaded third-party Chrome extension used for research (see its source when asked to "learn from" it) — not part of this project, not something to build on top of directly.
- `downloader/costco_receipt_downloader.js` is a standalone browser devtools console script — not imported by the Python app, has no pytest coverage, and a change to it never needs a Vercel redeploy. Validate with `node --check`.
- Costco's `receipts(startDate, endDate)` query silently omits gas station receipts; they're fetched separately via a `receiptsWithCounts` summary + per-barcode detail call (`documentType: "fuel"`) — see the comment on `graphqlRequest` in the downloader script before changing that flow.

## Discount/adjustment lines

Costco prints an instant-savings/coupon deduction as its own item-array row (description like `"/ 1937959"` or a non-numeric label like `"/SNAPS"`, negative amount) directly under the item it discounts. `normalize.py` flags these as `is_discount` and computes `net_amount` by folding each discount's amount onto the **nearest preceding non-discount row in the same receipt, by `line_no` order** — not by parsing an item number out of the description, since that reference isn't always numeric. Item-level views (`analytics/items.py`) exclude `is_discount` rows and sum `net_amount` (falls back to `amount` for older Parquet data predating that column).
