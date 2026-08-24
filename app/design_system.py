"""
Semiconductor Credit Intelligence
Professional HTML / CSS Design System
"""

from __future__ import annotations

import html
import textwrap

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio


# =============================================================================
# DESIGN TOKENS
# =============================================================================

NAVY = "#102A43"
NAVY_2 = "#163A59"

BLUE = "#2F76A8"
BLUE_LIGHT = "#76ACCF"

BACKGROUND = "#F4F7FA"
SURFACE = "#FFFFFF"

TEXT = "#152233"
TEXT_SOFT = "#344054"
MUTED = "#667085"

BORDER = "#E2E8F0"
GRID = "#E9EEF4"

GREEN = "#19725B"
GREEN_BG = "#E8F5F0"

AMBER = "#9B6718"
AMBER_BG = "#FFF4DE"

RED = "#A63E46"
RED_BG = "#FCEBED"


# =============================================================================
# HTML RENDERER
# =============================================================================

def render_html(markup: str):
    """
    Render actual HTML rather than passing indented HTML
    through Markdown.

    Uses st.html where available.
    """

    markup = textwrap.dedent(
        str(markup)
    ).strip()

    if hasattr(st, "html"):

        st.html(markup)

    else:

        st.markdown(
            markup,
            unsafe_allow_html=True
        )


# =============================================================================
# GLOBAL CSS
# =============================================================================

CSS = """
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@500;600&display=swap'
);


/* ==============================================================
   ROOT
   ============================================================== */

:root {

    --bank-navy: #102A43;
    --bank-navy-2: #163A59;

    --bank-blue: #2F76A8;

    --bank-bg: #F4F7FA;

    --bank-surface: #FFFFFF;

    --bank-text: #152233;

    --bank-soft: #344054;

    --bank-muted: #667085;

    --bank-border: #E2E8F0;

    --bank-green: #19725B;
    --bank-amber: #9B6718;
    --bank-red: #A63E46;

}


/* ==============================================================
   APP
   ============================================================== */

.stApp {

    background:
        linear-gradient(
            180deg,
            #F8FAFC 0%,
            #F3F6F9 100%
        );

}


.block-container {

    max-width: 1480px;

    padding-top: 1.65rem;
    padding-bottom: 4rem;

    padding-left: 2.25rem;
    padding-right: 2.25rem;

}


/* ==============================================================
   TYPOGRAPHY
   ============================================================== */

html,
body,
p,
span,
div,
button,
input,
textarea,
select,
label {

    font-family:
        "Inter",
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

}


h1,
h2,
h3,
h4 {

    font-family:
        "Inter",
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    color:
        var(--bank-text);

}


h1 {

    font-size:
        clamp(
            1.8rem,
            3vw,
            2.55rem
        ) !important;

    font-weight:
        800 !important;

    letter-spacing:
        -0.045em !important;

}


h2 {

    font-size:
        1.45rem !important;

    font-weight:
        700 !important;

    letter-spacing:
        -0.025em !important;

}


h3 {

    font-size:
        1.07rem !important;

    font-weight:
        700 !important;

}


/* ==============================================================
   SIDEBAR
   ============================================================== */

section[data-testid="stSidebar"] {

    background:

        linear-gradient(
            180deg,
            #0D2132 0%,
            #102A43 45%,
            #173C59 100%
        );

    border-right:
        1px solid
        rgba(
            255,
            255,
            255,
            0.06
        );

}


section[data-testid="stSidebar"] * {

    color:
        #F4F7FA;

}


section[data-testid="stSidebar"]
div[role="radiogroup"] label {

    border-radius:
        9px;

    transition:
        background
        150ms ease;

}


section[data-testid="stSidebar"]
div[role="radiogroup"] label:hover {

    background:
        rgba(
            255,
            255,
            255,
            0.065
        );

}


/* ==============================================================
   HERO
   ============================================================== */

.bank-hero {

    margin:
        0 0
        1.65rem 0;

}


.bank-eyebrow {

    color:
        var(--bank-blue);

    font-size:
        0.70rem;

    font-weight:
        800;

    letter-spacing:
        0.12em;

    text-transform:
        uppercase;

    margin-bottom:
        0.50rem;

}


.bank-title {

    color:
        var(--bank-text);

    font-family:
        "Inter",
        sans-serif;

    font-size:
        clamp(
            2rem,
            3.5vw,
            2.8rem
        );

    font-weight:
        800;

    letter-spacing:
        -0.055em;

    line-height:
        1.05;

}


.bank-subtitle {

    color:
        var(--bank-muted);

    max-width:
        820px;

    font-size:
        0.94rem;

    line-height:
        1.65;

    margin-top:
        0.75rem;

}


/* ==============================================================
   KPI CARDS
   ============================================================== */

.bank-kpi {

    position:
        relative;

    overflow:
        hidden;

    background:
        linear-gradient(
            180deg,
            #FFFFFF 0%,
            #FBFCFE 100%
        );

    border:
        1px solid
        var(--bank-border);

    border-radius:
        16px;

    min-height:
        124px;

    padding:
        1.12rem 1.15rem;

    box-shadow:

        0 2px 4px
        rgba(
            16,
            42,
            67,
            0.02
        ),

        0 10px 30px
        rgba(
            16,
            42,
            67,
            0.045
        );

    transition:

        transform
        180ms ease,

        box-shadow
        180ms ease,

        border-color
        180ms ease;

}


.bank-kpi::before {

    content: "";

    position:
        absolute;

    left:
        0;

    top:
        0;

    bottom:
        0;

    width:
        3px;

    background:
        var(--bank-blue);

    opacity:
        0.85;

}


.bank-kpi:hover {

    transform:
        translateY(-2px);

    border-color:
        #CFD9E3;

    box-shadow:

        0 4px 9px
        rgba(
            16,
            42,
            67,
            0.035
        ),

        0 15px 34px
        rgba(
            16,
            42,
            67,
            0.07
        );

}


.bank-kpi-label {

    color:
        var(--bank-muted);

    font-size:
        0.70rem;

    font-weight:
        800;

    letter-spacing:
        0.075em;

    text-transform:
        uppercase;

}


.bank-kpi-value {

    color:
        var(--bank-text);

    font-family:
        "IBM Plex Mono",
        "SFMono-Regular",
        monospace;

    font-size:
        clamp(
            1.45rem,
            2vw,
            1.85rem
        );

    font-weight:
        600;

    font-variant-numeric:
        tabular-nums;

    letter-spacing:
        -0.045em;

    margin-top:
        0.44rem;

}


.bank-kpi-note {

    color:
        var(--bank-muted);

    font-size:
        0.71rem;

    line-height:
        1.38;

    margin-top:
        0.40rem;

}


/* ==============================================================
   SECTION TITLE
   ============================================================== */

.bank-section {

    margin-top:
        1.55rem;

    margin-bottom:
        0.8rem;

}


.bank-section-title {

    color:
        var(--bank-text);

    font-size:
        1.10rem;

    font-weight:
        700;

    letter-spacing:
        -0.018em;

}


.bank-section-subtitle {

    color:
        var(--bank-muted);

    font-size:
        0.78rem;

    line-height:
        1.5;

    margin-top:
        0.20rem;

}


/* ==============================================================
   BADGES
   ============================================================== */

.bank-badge {

    display:
        inline-flex;

    align-items:
        center;

    padding:
        0.27rem 0.62rem;

    border-radius:
        999px;

    font-size:
        0.70rem;

    font-weight:
        750;

}


.bank-badge-green {

    background:
        #E8F5F0;

    color:
        #19725B;

}


.bank-badge-amber {

    background:
        #FFF4DE;

    color:
        #966515;

}


.bank-badge-red {

    background:
        #FCEBED;

    color:
        #A63E46;

}


.bank-badge-neutral {

    background:
        #EEF2F6;

    color:
        #475467;

}


/* ==============================================================
   DATAFRAME
   ============================================================== */

div[data-testid="stDataFrame"] {

    border:
        1px solid
        var(--bank-border);

    border-radius:
        14px;

    overflow:
        hidden;

    background:
        white;

    box-shadow:

        0 5px 22px
        rgba(
            16,
            42,
            67,
            0.035
        );

}


/* ==============================================================
   METRICS
   ============================================================== */

div[data-testid="stMetric"] {

    background:
        #FFFFFF;

    border:
        1px solid
        var(--bank-border);

    border-radius:
        14px;

    padding:
        1rem;

}


div[data-testid="stMetricValue"] {

    font-family:
        "IBM Plex Mono",
        monospace;

    font-variant-numeric:
        tabular-nums;

}


/* ==============================================================
   TABS
   ============================================================== */

button[data-baseweb="tab"] {

    border-radius:
        9px;

    font-weight:
        600;

}


button[data-baseweb="tab"]
[aria-selected="true"] {

    background:
        #EAF1F6;

}


/* ==============================================================
   INPUTS
   ============================================================== */

div[data-baseweb="select"] > div,
div[data-baseweb="input"] {

    border-radius:
        10px !important;

}


/* ==============================================================
   ALERTS
   ============================================================== */

div[data-testid="stAlert"] {

    border-radius:
        12px;

}


/* ==============================================================
   SCROLLBAR
   ============================================================== */

::-webkit-scrollbar {

    width:
        8px;

    height:
        8px;

}


::-webkit-scrollbar-thumb {

    background:
        #C4CDD6;

    border-radius:
        99px;

}


/* ==============================================================
   RESPONSIVE
   ============================================================== */

@media (
    max-width: 900px
) {

    .block-container {

        padding-left:
            1rem;

        padding-right:
            1rem;

    }


    .bank-title {

        font-size:
            1.8rem;

    }


    .bank-kpi {

        min-height:
            112px;

    }

}


/* ==============================================================
   TRANSITIONS
   ============================================================== */

.main .block-container {

    animation:
        bankFade
        220ms ease-out;

}


@keyframes bankFade {

    from {

        opacity:
            0;

        transform:
            translateY(
                3px
            );

    }

    to {

        opacity:
            1;

        transform:
            translateY(
                0
            );

    }

}

</style>
"""


# =============================================================================
# PLOTLY
# =============================================================================

CHART_CONFIG = {

    "displaylogo":
        False,

    "responsive":
        True,

    "scrollZoom":
        False,

    "doubleClick":
        "reset",

    "modeBarButtonsToRemove": [

        "lasso2d",

        "select2d",

        "toggleSpikelines"

    ]

}


def register_plotly_theme():

    theme = go.layout.Template()

    theme.layout = go.Layout(

        font=dict(

            family=
                "Inter, Segoe UI, Arial, sans-serif",

            size=
                12,

            color=
                TEXT

        ),

        paper_bgcolor=
            "rgba(0,0,0,0)",

        plot_bgcolor=
            "rgba(0,0,0,0)",

        margin=dict(

            l=35,

            r=22,

            t=55,

            b=42

        ),

        title=dict(

            font=dict(

                family=
                    "Inter, sans-serif",

                size=
                    16,

                color=
                    TEXT

            ),

            x=
                0.01,

            xanchor=
                "left"

        ),

        legend=dict(

            orientation=
                "h",

            yanchor=
                "bottom",

            y=
                1.02,

            xanchor=
                "right",

            x=
                1,

            font=dict(

                family=
                    "Inter, sans-serif",

                size=
                    10,

                color=
                    MUTED

            )

        ),

        hoverlabel=dict(

            bgcolor=
                "#FFFFFF",

            bordercolor=
                BORDER,

            font=dict(

                family=
                    "Inter, sans-serif",

                color=
                    TEXT

            )

        ),

        xaxis=dict(

            showgrid=
                False,

            zeroline=
                False,

            linecolor=
                BORDER,

            tickfont=dict(

                family=
                    "Inter, sans-serif",

                color=
                    MUTED

            ),

            automargin=
                True

        ),

        yaxis=dict(

            gridcolor=
                GRID,

            zeroline=
                False,

            tickfont=dict(

                family=
                    "Inter, sans-serif",

                color=
                    MUTED

            ),

            automargin=
                True

        ),

        colorway=[

            NAVY,

            BLUE,

            BLUE_LIGHT,

            GREEN,

            "#86754A",

            "#755D86",

            RED,

            "#6B7C8F"

        ]

    )

    pio.templates[
        "bank_v2"
    ] = theme

    pio.templates.default = (
        "bank_v2"
    )


def polish_chart(
    fig,
    height=None
):

    if fig is None:

        return fig


    try:

        fig.update_layout(

            template=
                "bank_v2",

            autosize=
                True,

            hovermode=
                "closest",

            transition=dict(

                duration=
                    200,

                easing=
                    "cubic-in-out"

            ),

            uirevision=
                "semiconductor-credit-ui"

        )


        if height is not None:

            fig.update_layout(
                height=height
            )


        fig.update_traces(

            selector=dict(
                type="bar"
            ),

            marker_line_width=
                0,

            opacity=
                0.93

        )


        fig.update_traces(

            selector=dict(
                type="scatter"
            ),

            marker=dict(
                size=7
            )

        )


    except Exception:

        pass


    return fig


# =============================================================================
# INITIALIZER
# =============================================================================

def initialize_design():

    register_plotly_theme()

    render_html(
        CSS
    )


# =============================================================================
# HERO
# =============================================================================

def hero(
    title,
    subtitle,
    eyebrow="SEMICONDUCTOR CREDIT INTELLIGENCE"
):

    title = html.escape(
        str(title)
    )

    subtitle = html.escape(
        str(subtitle)
    )

    eyebrow = html.escape(
        str(eyebrow)
    )


    render_html(
        f"""
        <div class="bank-hero">

            <div class="bank-eyebrow">
                {eyebrow}
            </div>

            <div class="bank-title">
                {title}
            </div>

            <div class="bank-subtitle">
                {subtitle}
            </div>

        </div>
        """
    )


# =============================================================================
# SECTION
# =============================================================================

def section(
    title,
    subtitle=None
):

    title = html.escape(
        str(title)
    )


    subtitle_html = ""


    if subtitle:

        subtitle_html = (
            '<div class="bank-section-subtitle">'
            + html.escape(
                str(subtitle)
            )
            + "</div>"
        )


    render_html(
        f"""
        <div class="bank-section">

            <div class="bank-section-title">
                {title}
            </div>

            {subtitle_html}

        </div>
        """
    )


# =============================================================================
# KPI
# =============================================================================

def kpi(
    label,
    value,
    note=""
):

    label = html.escape(
        str(label)
    )

    value = html.escape(
        str(value)
    )

    note = html.escape(
        str(note)
    )


    render_html(
        f"""
        <div class="bank-kpi">

            <div class="bank-kpi-label">
                {label}
            </div>

            <div class="bank-kpi-value">
                {value}
            </div>

            <div class="bank-kpi-note">
                {note}
            </div>

        </div>
        """
    )


# =============================================================================
# BADGE
# =============================================================================

def badge(
    value
):

    safe_value = html.escape(
        "Not available"
        if value is None
        else str(value)
    )


    normalized = (
        safe_value
        .strip()
        .upper()
    )


    if normalized in {
        "GREEN",
        "A"
    }:

        css_class = (
            "bank-badge-green"
        )


    elif normalized in {
        "AMBER",
        "B",
        "C"
    }:

        css_class = (
            "bank-badge-amber"
        )


    elif normalized in {
        "RED",
        "D",
        "E"
    }:

        css_class = (
            "bank-badge-red"
        )


    else:

        css_class = (
            "bank-badge-neutral"
        )


    return (
        f'<span class="bank-badge '
        f'{css_class}">'
        f'{safe_value}'
        f'</span>'
    )
