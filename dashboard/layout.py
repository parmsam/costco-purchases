"""Shared page shell + navigation bar."""

from fasthtml.common import Div, Script, Style, Titled
from monsterui.core import Theme, ThemeRadii
from monsterui.franken import A, Button, ButtonT, DivLAligned, NavBar, Subtitle, UkIcon, H2

# Neither franken-ui nor daisyUI sets a default text/background color on
# <body>/<html> — Pico.css was quietly doing that (and, since Pico follows
# the OS's own dark-mode preference independent of this app's toggle, doing
# it inconsistently whenever the two disagreed — the actual cause of the
# dark-tables/washed-out-headings bugs). Disabling Pico (app.py, pico=False)
# removes that conflict, but this app-level rule has to replace the base
# color Pico was otherwise providing, or unstyled text would fall back to
# plain black and vanish in dark mode.
BASE_COLOR_STYLE = Style("""
body { background-color: hsl(var(--background)); color: hsl(var(--foreground)); }
/* FastHTML's Titled() wraps every page in <main class="container">. Pico
   was the one giving that a centered max-width; Tailwind's own .container
   utility (now the only one matching) sets a max-width per breakpoint but,
   unlike Pico's, doesn't auto-center by default. Restoring just the
   centering here, since removing Pico dropped it. */
main.container { margin-left: auto; margin-right: auto; }
""")

# MonsterUI's own header script already reads a "__FRANKEN__" localStorage
# key and applies the "dark" class based on it, falling back to
# prefers-color-scheme when no mode is stored — that's the "system default"
# behavior. This adds the missing piece: a visible toggle that cycles
# system -> light -> dark, writing to that same key so nothing conflicts.
THEME_TOGGLE_SCRIPT = Script("""
function _frankenState() {
  try { return JSON.parse(localStorage.getItem('__FRANKEN__') || '{}'); } catch (e) { return {}; }
}
function _applyThemeMode(mode) {
  var isDark = mode === 'dark' || (mode !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark', isDark);
  var icon = document.getElementById('theme-toggle-icon');
  if (icon) icon.setAttribute('icon', !mode ? 'monitor' : (mode === 'dark' ? 'moon' : 'sun'));
}
function cycleTheme() {
  var state = _frankenState();
  var order = ['system', 'light', 'dark'];
  var current = state.mode || 'system';
  var next = order[(order.indexOf(current) + 1) % order.length];
  if (next === 'system') { delete state.mode; } else { state.mode = next; }
  localStorage.setItem('__FRANKEN__', JSON.stringify(state));
  _applyThemeMode(state.mode);
}
document.addEventListener('DOMContentLoaded', function () { _applyThemeMode(_frankenState().mode); });
""")

# Generic click-to-sort for any table built via components.sortable_table().
# Parses each cell in the clicked column as a number (stripping $, commas,
# %) when possible, falling back to case-insensitive string comparison —
# so it works unmodified across every table in the app without per-table
# server code.
TABLE_SORT_SCRIPT = Script("""
function sortTableBy(th) {
  var table = th.closest('table');
  var tbody = table.querySelector('tbody');
  var headerRow = th.parentElement;
  var cellIndex = Array.prototype.indexOf.call(headerRow.children, th);
  var nextDir = th.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';

  Array.prototype.forEach.call(headerRow.children, function (h) {
    h.removeAttribute('data-sort-dir');
    var ind = h.querySelector('.sort-indicator');
    if (ind) ind.textContent = '';
  });
  th.setAttribute('data-sort-dir', nextDir);
  var indicator = th.querySelector('.sort-indicator');
  if (indicator) indicator.textContent = nextDir === 'asc' ? ' \\u25B2' : ' \\u25BC';

  function cellValue(tr) {
    var cell = tr.children[cellIndex];
    var text = (cell.textContent || '').trim();
    var cleaned = text.replace(/[$,%]/g, '');
    var num = parseFloat(cleaned);
    var isNumeric = cleaned !== '' && !isNaN(num) && /^-?\\d+(\\.\\d+)?$/.test(cleaned);
    return isNumeric ? num : text.toLowerCase();
  }

  var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
  rows.sort(function (a, b) {
    var av = cellValue(a), bv = cellValue(b);
    if (typeof av === 'number' && typeof bv === 'number') {
      return nextDir === 'asc' ? av - bv : bv - av;
    }
    av = String(av); bv = String(bv);
    return nextDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
  });
  rows.forEach(function (r) { tbody.appendChild(r); });
}
""")

NAV_LINKS = [
    ("Dashboard", "/dashboard", "layout-dashboard"),
    ("Trends", "/trends", "trending-up"),
    ("Items", "/items", "shopping-cart"),
    ("Warehouses", "/warehouses", "warehouse"),
    ("Departments", "/departments", "layers"),
    ("Payments", "/payments", "credit-card"),
    ("Upload", "/upload", "upload"),
]

PAGE_ICONS = {label: icon for label, _, icon in NAV_LINKS}
PAGE_ICONS["Receipt"] = "receipt"


def nav_bar(active: str = ""):
    links = [
        A(
            UkIcon(icon, height=16, width=16),
            label,
            href=href,
            cls=(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold "
                "bg-primary/10 text-primary"
                if href == active
                else "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm text-muted-foreground "
                "hover:bg-primary/5 hover:text-primary transition-colors"
            ),
        )
        for label, href, icon in NAV_LINKS
    ]
    brand = DivLAligned(
        UkIcon("shopping-cart", height=20, width=20, cls="text-primary"),
        Div("Costco Purchases", cls="font-bold text-lg"),
        cls="gap-2",
    )
    theme_toggle = Button(
        UkIcon("monitor", height=16, width=16, id="theme-toggle-icon"),
        id="theme-toggle-btn",
        cls=(ButtonT.ghost, "rounded-full px-2"),
        onclick="cycleTheme()",
        submit=False,
        title="Toggle theme (system / light / dark)",
    )
    return NavBar(
        *links,
        theme_toggle,
        brand=brand,
        sticky=True,
        cls="px-4 py-2.5 border-b border-border/60 backdrop-blur bg-background/95",
    )


def page(title: str, *content, active: str = "", subtitle: str = "", filter_bar=None):
    icon = PAGE_ICONS.get(title)
    header = Div(
        DivLAligned(
            UkIcon(icon, height=26, width=26, cls="text-primary") if icon else "",
            H2(title, cls="font-bold"),
            cls="gap-2.5",
        ),
        Subtitle(subtitle) if subtitle else "",
        cls="mb-6",
    )
    return Titled(
        title,
        Div(nav_bar(active), cls="mb-8"),
        Div(
            header,
            filter_bar if filter_bar is not None else "",
            *content,
            cls="container mx-auto px-4 pb-16 max-w-6xl",
        ),
    )


theme_headers = (
    *Theme.blue.headers(radii=ThemeRadii.md),
    BASE_COLOR_STYLE,
    THEME_TOGGLE_SCRIPT,
    TABLE_SORT_SCRIPT,
)
