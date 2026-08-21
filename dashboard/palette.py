"""Chart color palette and chrome — validated categorical hues (light mode).

Charts render via server-side Plotly at request time with fixed colors, so
they intentionally stay light-mode-consistent rather than following the
viewer's OS/browser dark-mode preference (MonsterUI's own components already
do). Syncing Plotly's rendered theme to client dark mode would need extra
client-side JS to re-theme after load; treated as a known v1 limitation.
"""

# Ordered categorical palette — colorblind-safe adjacent pairs. Use in this
# fixed order; never cycle or reassign per selection. Single-series charts
# (most of this dashboard's bar charts) use only CATEGORICAL[0].
CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SINGLE_SERIES = CATEGORICAL[0]

CHART_FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
