"""Plotly figure -> FastHTML element rendering, styled to match the app chrome."""

from fasthtml.common import Div
from fh_plotly import plotly2fasthtml
from monsterui.franken import Card, CardBody

from dashboard.palette import BASELINE, CHART_FONT, GRIDLINE, MUTED_INK, PRIMARY_INK, SURFACE


def chart_card(fig, height: int = 380):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=48, r=24, t=16, b=48),
        font=dict(family=CHART_FONT, color=PRIMARY_INK, size=13),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        hoverlabel=dict(bgcolor="#ffffff", font_size=13, font_family=CHART_FONT),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, linecolor=BASELINE, tickfont=dict(color=MUTED_INK), title_font=dict(color=MUTED_INK))
    fig.update_yaxes(gridcolor=GRIDLINE, linecolor=BASELINE, tickfont=dict(color=MUTED_INK), title_font=dict(color=MUTED_INK), zeroline=False)

    return Card(
        CardBody(
            Div(
                plotly2fasthtml(fig, js_options={"displayModeBar": False, "responsive": True}),
                cls="w-full",
            )
        )
    )
