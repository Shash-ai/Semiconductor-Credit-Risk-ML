from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

NAVY = "#0B1F33"
INK = "#111827"
MUTED = "#667085"
BLUE = "#2563EB"
TEAL = "#0F766E"
GREEN = TEAL
AMBER = "#D97706"
RED = "#DC2626"
PURPLE = "#7C3AED"
SLATE = "#475569"
BORDER = "#E5E7EB"
GRID = "#EEF2F6"
SURFACE = "#FFFFFF"
BACKGROUND = "#F7F8FA"

EWS_COLORS = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED}
GRADE_COLORS = {"A": GREEN, "B": "#3B82F6", "C": AMBER, "D": "#EA580C", "E": RED}

PLOTLY_CONFIG = {
    "displaylogo": False,
    "displayModeBar": "hover",
    "responsive": True,
    "scrollZoom": False,
    "doubleClick": "reset",
    "modeBarButtonsToAdd": ["drawline"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "semiconductor_credit_chart",
        "height": 900,
        "width": 1500,
        "scale": 2,
    },
}

CSS = r"""
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.stApp { background: #F7F8FA; }
.block-container {
    max-width: 1500px;
    padding-top: 1.25rem;
    padding-bottom: 3rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
h1, h2, h3, h4 { color: #111827 !important; letter-spacing: -0.02em; }
p, li, label, .stCaption, [data-testid="stMarkdownContainer"] { color: #334155; }
[data-testid="stSidebar"] {
    background: #0B1F33;
    border-right: 1px solid #16324A;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: #F8FAFC !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: .35rem .45rem;
    border-radius: 8px;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.06); }
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 0.95rem 1rem;
    min-height: 108px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}
[data-testid="stMetricLabel"] { color: #64748B !important; font-weight: 600; }
[data-testid="stMetricValue"] {
    color: #111827 !important;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.035em;
}
[data-testid="stMetricDelta"] { font-size: .76rem; }
[data-testid="stDataFrame"] {
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    overflow: hidden;
}
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-color: #E5E7EB !important;
    border-radius: 12px !important;
    background: #FFFFFF;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    background: #FFFFFF !important;
    color: #111827 !important;
}
button[data-baseweb="tab"] { font-weight: 600; }
.stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 600; }
div[data-testid="stAlert"] { border-radius: 10px; }
hr { border-color: #E5E7EB !important; }
.sci-eyebrow {
    color: #2563EB;
    font-size: .72rem;
    font-weight: 750;
    letter-spacing: .10em;
    text-transform: uppercase;
    margin-bottom: .35rem;
}
.sci-title {
    color: #111827;
    font-size: clamp(1.85rem, 3vw, 2.55rem);
    font-weight: 760;
    letter-spacing: -.045em;
    line-height: 1.08;
    margin: 0;
}
.sci-subtitle {
    color: #64748B;
    font-size: .93rem;
    line-height: 1.55;
    max-width: 880px;
    margin-top: .55rem;
    margin-bottom: 1.25rem;
}
.sci-section-title {
    color: #111827;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -.015em;
    margin-bottom: .15rem;
}
.sci-section-note {
    color: #64748B;
    font-size: .78rem;
    margin-bottom: .65rem;
}
@media (max-width: 900px) {
    .block-container { padding-left: .9rem; padding-right: .9rem; }
}
</style>
"""


def apply_ui() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, eyebrow: str = "SEMICONDUCTOR CREDIT INTELLIGENCE") -> None:
    st.markdown(
        f"""
        <div class="sci-eyebrow">{eyebrow}</div>
        <div class="sci-title">{title}</div>
        <div class="sci-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, note: str = "") -> None:
    st.markdown(
        f'<div class="sci-section-title">{title}</div>'
        + (f'<div class="sci-section-note">{note}</div>' if note else ""),
        unsafe_allow_html=True,
    )


def style_figure(fig: go.Figure, *, height: int = 390) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif',
            color=INK,
            size=12,
        ),
        margin=dict(l=24, r=20, t=34, b=34),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER, font_color=INK),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11, color=MUTED),
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=BORDER,
            tickfont=dict(color=MUTED),
            title_font=dict(color=MUTED),
            automargin=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRID,
            zeroline=False,
            linecolor=BORDER,
            tickfont=dict(color=MUTED),
            title_font=dict(color=MUTED),
            automargin=True,
        ),
        hovermode="closest",
        dragmode="pan",
        uirevision="sci-stable",
    )
    return fig


def show_plotly(fig: go.Figure, *, key: str, height: int = 390, selectable: bool = False):
    style_figure(fig, height=height)
    kwargs = dict(
        width="stretch",
        theme=None,
        config=PLOTLY_CONFIG,
        key=key,
    )
    if selectable:
        kwargs.update(on_select="rerun", selection_mode=("points", "box", "lasso"))
    return st.plotly_chart(fig, **kwargs)
