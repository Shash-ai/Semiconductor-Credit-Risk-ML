from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

import banking_dashboard_v3 as ui


EXTRA_CSS = r"""
<style>
.sci-kv-grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:.72rem;
    margin:.4rem 0 1rem 0;
}
.sci-kv{
    background:#FFFFFF;
    border:1px solid #E4E7EC;
    border-radius:10px;
    padding:.78rem .86rem;
    min-width:0;
    box-shadow:0 1px 2px rgba(16,24,40,.02);
}
.sci-kv-label{
    color:#667085;
    font-size:.68rem;
    font-weight:720;
    letter-spacing:.045em;
    text-transform:uppercase;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
}
.sci-kv-value{
    color:#101828;
    font-size:.88rem;
    font-weight:650;
    line-height:1.42;
    margin-top:.25rem;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    word-break:break-word!important;
}
.sci-table-wrap{
    width:100%;
    overflow-x:auto;
    border:1px solid #E4E7EC;
    border-radius:10px;
    background:#FFFFFF;
    margin:.4rem 0 1rem 0;
}
.sci-table{
    width:100%;
    border-collapse:collapse;
    table-layout:fixed;
    font-size:.78rem;
}
.sci-table th{
    text-align:left;
    vertical-align:top;
    color:#475467;
    background:#F9FAFB;
    border-bottom:1px solid #E4E7EC;
    padding:.65rem .72rem;
    font-weight:720;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    word-break:break-word!important;
}
.sci-table td{
    vertical-align:top;
    color:#344054;
    border-bottom:1px solid #F0F2F5;
    padding:.65rem .72rem;
    line-height:1.45;
    white-space:normal!important;
    overflow-wrap:anywhere!important;
    word-break:break-word!important;
}
.sci-table tr:last-child td{border-bottom:none;}
.sci-empty-value{color:#98A2B3;font-weight:600;}
[data-testid="stMetricValue"] > div,
[data-testid="stMetricLabel"] > div,
[data-testid="stMetricDelta"] > div{
    white-space:normal!important;
    overflow:visible!important;
    text-overflow:clip!important;
    overflow-wrap:anywhere!important;
}
[data-testid="stDataFrame"]{
    overflow:visible!important;
}
[data-testid="stDataFrame"] *{
    text-overflow:clip!important;
}
@media(max-width:900px){
    .sci-kv-grid{grid-template-columns:1fr;}
    .sci-table{table-layout:auto;}
}
</style>
"""


def _esc(value: Any) -> str:
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "not available", "not_available"}:
        return "—"
    return html.escape(text)


def _render_html(markup: str):
    markup = markup.strip()
    if hasattr(st, "html"):
        st.html(markup)
    else:
        st.markdown(markup, unsafe_allow_html=True)


def header(title: str, subtitle: str):
    markup = (
        '<div class="sci-topline">'
        '<div class="sci-brandline"><span class="sci-dot"></span>Semiconductor Credit Intelligence</div>'
        '<div class="sci-status">RESEARCH · CONTROLLED PILOT</div>'
        '</div>'
        f'<div class="sci-title">{_esc(title)}</div>'
        f'<div class="sci-subtitle">{_esc(subtitle)}</div>'
        '<div class="sci-rule"></div>'
    )
    _render_html(markup)


def card(label: str, value: Any, note: Any | None = None):
    value_html = _esc(value)
    if value_html == "—":
        value_html = '<span class="sci-empty-value">Not available</span>'
    note_html = f'<div class="sci-note">{_esc(note)}</div>' if note else ""
    markup = (
        '<div class="sci-card">'
        f'<div class="sci-card-label">{_esc(label)}</div>'
        f'<div class="sci-card-value">{value_html}</div>'
        f'{note_html}'
        '</div>'
    )
    _render_html(markup)


def state_panel(title: str, body: str, foot: str | None = None, tone: str = "info"):
    safe_tone = tone if tone in {"info", "warn", "good"} else "info"
    foot_html = f'<div class="sci-state-foot">{_esc(foot)}</div>' if foot else ""
    markup = (
        f'<div class="sci-state {safe_tone}">'
        f'<div class="sci-state-title">{_esc(title)}</div>'
        f'<div class="sci-state-body">{_esc(body)}</div>'
        f'{foot_html}'
        '</div>'
    )
    _render_html(markup)


def detail_grid(items: list[tuple[str, Any]]):
    cells = []
    for label, value in items:
        value_html = _esc(value)
        if value_html == "—":
            value_html = '<span class="sci-empty-value">Not available</span>'
        cells.append(
            '<div class="sci-kv">'
            f'<div class="sci-kv-label">{_esc(label)}</div>'
            f'<div class="sci-kv-value">{value_html}</div>'
            '</div>'
        )
    _render_html('<div class="sci-kv-grid">' + ''.join(cells) + '</div>')


def wrapped_table(df: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 50):
    if df is None or df.empty:
        st.caption("No records available.")
        return

    work = df.copy()
    if columns is not None:
        cols = [c for c in columns if c in work.columns]
        if not cols:
            st.caption("No displayable fields are available.")
            return
        work = work[cols]

    work = work.head(max_rows)
    head = ''.join(f'<th>{_esc(ui.readable_label(c))}</th>' for c in work.columns)
    rows = []

    for _, row in work.iterrows():
        cells = []
        for col in work.columns:
            raw = row[col]
            if isinstance(raw, str) and raw.startswith(("http://", "https://")):
                safe_url = html.escape(raw, quote=True)
                cell = f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">Open source</a>'
            else:
                cell = _esc(raw)
                if cell == "—":
                    cell = '<span class="sci-empty-value">Not available</span>'
            cells.append(f'<td>{cell}</td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')

    markup = (
        '<div class="sci-table-wrap">'
        '<table class="sci-table">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
        '</div>'
    )
    _render_html(markup)

    if len(df) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(df)} records.")


def install_patch():
    ui.header = header
    ui.card = card
    ui.state_panel = state_panel
    ui.detail_grid = detail_grid
    ui.wrapped_table = wrapped_table
    ui.CSS = ui.CSS + EXTRA_CSS


def render_app():
    install_patch()
    ui.render_app()
