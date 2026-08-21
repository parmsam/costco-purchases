"""Post-process crawled dashboard HTML into a static GitHub Pages site.

Input: raw HTML files crawled from the live app (dashboard.html, trends.html,
items.html, warehouses.html, departments.html, payments.html, upload.html,
receipt.html) in --raw-dir.

Rewrites server-relative links/routes to relative static filenames, disables
the interactions that need a real backend (live item search, upload forms),
and adds a banner noting this is a static demo with synthetic data. Writes
the result to --out-dir along with an index.html that redirects to
dashboard.html.
"""

import argparse
import re
from pathlib import Path

PAGES = ["dashboard", "trends", "items", "warehouses", "departments", "payments", "upload"]

BANNER = """
<div style="background:#eef2ff;border-bottom:1px solid #c7d2fe;padding:10px 16px;text-align:center;font-size:13px;font-family:system-ui,-apple-system,sans-serif;color:#312e81;">
  📊 Static demo with synthetic sample data — not your real purchases. Live search and file upload are disabled here.
  <a href="https://github.com/parmsam/costco-purchases" style="color:#4338ca;font-weight:600;">Run it yourself →</a>
</div>
""".strip()


DEMO_SITE_BASE = "https://parmsam.github.io/costco-purchases"


def rewrite_links(html: str, page_name: str) -> str:
    # Nav links / filter-bar form actions / preset links to our own pages.
    for page in PAGES:
        html = re.sub(rf'(href|action)="/{page}(\?[^"]*)?"', rf'\1="{page}.html"', html)
    # Any receipt detail link -> the single sample receipt page we saved.
    html = re.sub(r'href="/receipt/[^"]*"', 'href="receipt.html"', html)
    # FastHTML auto-emits <link rel="canonical" href="https://localhost:5001/...">
    # — point it at the real public URL instead of leaking the local dev host.
    html = re.sub(
        r'<link rel="canonical" href="[^"]*">',
        f'<link rel="canonical" href="{DEMO_SITE_BASE}/{page_name}.html">',
        html,
    )
    return html


def disable_backend_bits(html: str) -> str:
    # Live item search hits /items/table via htmx — no backend here, so
    # strip the hx-* wiring and make it clear the box doesn't do anything.
    html = html.replace('hx-get="/items/table"', "")
    html = re.sub(
        r'placeholder="Search items\.\.\."',
        'placeholder="Search (disabled in this static demo)" disabled',
        html,
    )
    # Upload forms can't actually process a file without a server.
    html = re.sub(r'action="/upload/(json|csv)"', 'action="#" onsubmit="return false;"', html)
    return html


def inject_banner(html: str) -> str:
    return html.replace("<body>", f"<body>\n{BANNER}", 1)


def process(src: Path, dst: Path, page_name: str) -> None:
    html = src.read_text()
    html = rewrite_links(html, page_name)
    html = disable_backend_bits(html)
    html = inject_banner(html)
    dst.write_text(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    for page in PAGES:
        process(args.raw_dir / f"{page}.html", args.out_dir / f"{page}.html", page)
        print(f"wrote {page}.html")

    process(args.raw_dir / "receipt.html", args.out_dir / "receipt.html", "receipt")
    print("wrote receipt.html")

    (args.out_dir / "index.html").write_text(
        '<!doctype html><meta http-equiv="refresh" content="0; url=dashboard.html">'
        '<a href="dashboard.html">Continue to the demo dashboard</a>'
    )
    print("wrote index.html")


if __name__ == "__main__":
    main()
