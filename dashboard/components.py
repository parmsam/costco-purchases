"""Small reusable MonsterUI-wrapped components."""

from datetime import datetime, timedelta

from fasthtml.common import Div, Form, Span, Table, Tbody, Td, Th, Thead, Tr
from monsterui.franken import A, Button, ButtonT, Card, CardT, DivLAligned, H4, LabelInput, P, UkIcon


def kpi_card(label: str, value: str, sub: str = "", icon: str = "circle"):
    return Card(
        Div(
            Div(
                UkIcon(icon, height=18, width=18, cls="text-primary"),
                cls="shrink-0 grid place-items-center w-9 h-9 rounded-full bg-primary/10",
            ),
            Div(
                P(label, cls="text-muted-foreground text-xs font-medium uppercase tracking-wide"),
                Div(value, cls="text-xl sm:text-2xl font-bold leading-tight break-words"),
                P(sub, cls="text-muted-foreground text-xs mt-0.5") if sub else "",
            ),
            cls="flex items-start gap-3",
        ),
        cls=(CardT.hover, "p-4"),
    )


def kpi_row(*cards):
    return Div(*cards, cls="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8")


def section(title: str, *content, icon: str = "", controls=None):
    title_group = DivLAligned(
        UkIcon(icon, height=17, width=17, cls="text-muted-foreground") if icon else "",
        H4(title),
        cls="gap-2",
    )
    heading = (
        Div(title_group, controls, cls="flex items-center justify-between mb-3")
        if controls is not None
        else Div(title_group, cls="mb-3")
    )
    return Div(heading, *content, cls="mb-10")


def limit_select(path: str, current: int, options: list[int], hidden_fields: dict, label: str = "Show"):
    """A GET-form <select> (auto-submits on change) for a 'how many rows' control.

    Plain native <select> rather than MonsterUI's LabelSelect — that one
    renders as a JS-enhanced custom element with its own event handling,
    which isn't guaranteed to fire a plain `onchange`. A native <select>
    styled with franken-ui's `uk-select` class is predictable and doesn't
    depend on that component's internals.
    """
    from fasthtml.common import Input, Option, Select

    opts = [Option(str(n), value=str(n), selected=(n == current)) for n in options]
    opts.append(Option("All", value="0", selected=(current == 0)))
    return Form(
        *[Input(type="hidden", name=k, value=v) for k, v in hidden_fields.items() if v],
        Span(label, cls="text-sm text-muted-foreground mr-2"),
        Select(*opts, name="limit", onchange="this.form.submit()", cls="uk-select w-auto text-sm py-1"),
        action=path,
        method="get",
        cls="flex items-center",
    )


def _sortable_th(text):
    return Th(
        Span(text, Span(cls="sort-indicator ml-1 text-xs"), cls="inline-flex items-center"),
        onclick="sortTableBy(this)",
        cls=(
            "text-left font-medium text-xs uppercase tracking-wide text-muted-foreground "
            "px-3 py-2 cursor-pointer select-none hover:text-primary whitespace-nowrap"
        ),
        style="background-color:transparent;",
    )


_NEUTRALIZE = "background-color:transparent;color:inherit;"


def sortable_table(header_data, body_data):
    """A plain HTML table with click-to-sort headers, immune to page CSS.

    Pico.css (loaded classless, styling bare <table>/<thead>/<tr> tags
    directly) follows the OS's prefers-color-scheme independently of this
    app's own theme toggle, so it can paint the table dark even while the
    rest of the page is light. Utility classes (even `!important`-prefixed
    ones) depend on the Tailwind CDN script's runtime compilation, which
    isn't guaranteed — so every row/cell here carries a plain inline
    `style` instead. An inline style always wins over any external
    stylesheet rule that isn't itself `!important` (Pico's isn't), which
    is a CSS-cascade guarantee rather than a framework-specific guess.
    """
    thead = Thead(
        Tr(*[_sortable_th(h) for h in header_data], style=_NEUTRALIZE),
        cls="border-b border-border",
        style=_NEUTRALIZE,
    )
    rows = [
        Tr(
            *[Td(row.get(h, ""), cls="px-3 py-2 align-top", style=_NEUTRALIZE) for h in header_data],
            cls="border-b border-border/50 last:border-0 hover:bg-foreground/5 transition-colors",
            style=_NEUTRALIZE,
        )
        for row in body_data
    ]
    return Div(
        Table(thead, Tbody(*rows, style=_NEUTRALIZE), cls="w-full text-sm", style=_NEUTRALIZE),
        cls="overflow-x-auto",
    )


def date_range_filter(path: str, start: str = "", end: str = "", min_date: str = "", max_date: str = ""):
    today = datetime.now().date()
    presets = [
        ("Last 30 Days", (today - timedelta(days=30)).isoformat(), today.isoformat()),
        ("Last 90 Days", (today - timedelta(days=90)).isoformat(), today.isoformat()),
        ("This Year", f"{today.year}-01-01", today.isoformat()),
        ("All Time", "", ""),
    ]
    preset_links = [
        A(
            label,
            href=f"{path}?start={s}&end={e}" if s else path,
            cls="text-xs px-2.5 py-1 rounded-full bg-muted hover:bg-primary/10 hover:text-primary transition-colors",
        )
        for label, s, e in presets
    ]
    return Card(
        Form(
            Div(*preset_links, cls="flex flex-wrap gap-1.5 mb-3"),
            Div(
                LabelInput(
                    "From", type="date", name="start", value=start or "", min=min_date, max=max_date, cls="space-y-1"
                ),
                LabelInput(
                    "To", type="date", name="end", value=end or "", min=min_date, max=max_date, cls="space-y-1"
                ),
                Button("Apply", cls=ButtonT.primary, submit=True),
                cls="flex flex-wrap items-end gap-3",
            ),
            action=path,
            method="get",
        ),
        cls="mb-6 p-4",
    )


def empty_state(message: str, icon: str = "inbox", cta_label: str = "Go to Upload", cta_href: str = "/upload"):
    return Card(
        Div(
            UkIcon(icon, height=36, width=36, cls="text-muted-foreground/50"),
            P(message, cls="text-muted-foreground max-w-md"),
            A(cta_label, href=cta_href, cls=(ButtonT.primary, "uk-btn")),
            cls="flex flex-col items-center text-center gap-3 py-12 px-6",
        )
    )
