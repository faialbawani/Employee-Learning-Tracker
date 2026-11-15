"""
Al Bawani | Learning & Development Dashboard
=============================================
Streamlit dashboard for LinkedIn Learning reports.

File layout (top to bottom)
  1. Settings and design system (CSS)
  2. UI helpers (HTML cards, tables, charts)
  3. Report reading and validation
  4. Data preparation
  5. Analytics (mandatory program, optional learning, monthly history)
  6. Sidebar, data loading, filters, KPIs
  7. Tabs: Overview | Employee Tracking | Course Analytics |
           Mandatory Program | Monthly History

Data handling: this app does not write uploaded reports to disk or to a
database. Everything is processed in memory for the current session. The
only long-term record is the Historical Archive CSV that you download.
"""

from __future__ import annotations

import csv
import difflib
import html as html_lib
import inspect
import io
import re
import unicodedata
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==================================================
# 1. SETTINGS
# ==================================================

st.set_page_config(
    page_title="Al Bawani | Learning Hub",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Optional: pre-fill the three mandatory course titles for everyone who opens
# the app. Leave as "" to type them in the sidebar instead.
DEFAULT_MANDATORY_COURSES = ["", "", ""]

LOGO_FILE = "AL-Bawani-logo.png"

GREEN = "#08783E"
DARK_GREEN = "#075B32"
MID_GREEN = "#2A9B60"
LIGHT_GREEN = "#7CC59B"
PALE_GREEN = "#DCE9E0"
GOLD = "#C6A45B"
INK = "#1E3328"
MUTED = "#6F7F76"
GRID = "#EEF2EF"
FONT_STACK = "Inter, 'Segoe UI', Tahoma, Arial, sans-serif"
PALETTE = [GREEN, GOLD, MID_GREEN, LIGHT_GREEN, "#9AA89F", DARK_GREEN]
STATUS_COLORS = {
    "Completed": GREEN,
    "In Progress": GOLD,
    "Not Started": "#C9D3CD",
}

MATCH_EXACT = "Exact title"
MATCH_CONTAINS = "Title contains text"

# ==================================================
# DESIGN SYSTEM
# ==================================================

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --green: #08783E;
    --green-dark: #075B32;
    --green-mid: #2A9B60;
    --gold: #C6A45B;
    --ink: #1E3328;
    --muted: #6F7F76;
    --line: #E2EAE5;
    --bg: #F3F6F4;
}

html, body, .stApp, .stMarkdown, p, label, input, textarea, button,
li, td, th, h1, h2, h3, h4, h5, h6 {
    font-family: Inter, 'Segoe UI', Tahoma, Arial, sans-serif;
}

.stApp { background: var(--bg); color: var(--ink); }

.block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 1.6rem;
    padding-bottom: 3rem;
    max-width: 1320px;
}

[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed #B9D3C3;
    border-radius: 12px;
    background: #F8FBF9;
}

.side-brand {
    font-size: 11px; letter-spacing: .16em; font-weight: 800;
    color: var(--green-dark); margin: 0 0 2px;
}
.side-sub { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.side-label {
    font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
    font-weight: 800; color: var(--muted); margin: 18px 0 6px;
}

/* ---------- header ---------- */
.eyebrow {
    font-size: 11px; letter-spacing: .18em; font-weight: 800;
    color: var(--gold); text-transform: uppercase;
}
.app-title {
    font-size: 27px; font-weight: 800; color: var(--green-dark);
    line-height: 1.2; margin-top: 2px;
}
.gold-rule {
    height: 3px; width: 100%; margin: 14px 0 14px; border-radius: 2px;
    background: linear-gradient(90deg, var(--gold), rgba(198,164,91,.15) 55%, transparent);
}
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 6px; }
.chip {
    background: #fff; border: 1px solid var(--line); border-radius: 999px;
    padding: 5px 13px; font-size: 12px; color: var(--muted);
}
.chip b { color: var(--green-dark); font-weight: 700; }
.chip-gold { border-color: rgba(198,164,91,.55); background: #FFFBF1; }

/* ---------- section titles ---------- */
.sec {
    font-size: 18px; font-weight: 700; color: #17452F;
    margin: 28px 0 14px; position: relative; padding-bottom: 9px;
}
.sec::after {
    content: ""; position: absolute; left: 0; bottom: 0;
    width: 34px; height: 3px; background: var(--gold); border-radius: 2px;
}

/* ---------- KPI cards ---------- */
.kpi-grid {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px; margin: 6px 0 20px;
}
@media (max-width: 1000px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 520px)  { .kpi-grid { grid-template-columns: 1fr; } }
.kpi {
    background: #fff; border: 1px solid var(--line);
    border-left: 4px solid var(--green); border-radius: 14px;
    padding: 16px 18px; box-shadow: 0 2px 10px rgba(20,60,40,.04);
    transition: transform .25s ease, box-shadow .25s ease;
    animation: fadeUp .55s ease both;
}
.kpi:nth-child(2) { animation-delay: .04s; } .kpi:nth-child(3) { animation-delay: .08s; }
.kpi:nth-child(4) { animation-delay: .12s; } .kpi:nth-child(5) { animation-delay: .16s; }
.kpi:nth-child(6) { animation-delay: .2s; }  .kpi:nth-child(7) { animation-delay: .24s; }
.kpi:nth-child(8) { animation-delay: .28s; }
.kpi:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(8,120,62,.12); }
.kpi-gold { border-left-color: var(--gold); }
.kpi-label {
    font-size: 11px; letter-spacing: .09em; text-transform: uppercase;
    color: var(--muted); font-weight: 700;
}
.kpi-value {
    font-size: 28px; font-weight: 800; color: var(--green-dark);
    line-height: 1.15; margin-top: 6px;
}
.kpi-sub { font-size: 12px; color: var(--muted); margin-top: 4px; min-height: 16px; }

/* ---------- cards, bars, pills ---------- */
.card {
    background: #fff; border: 1px solid var(--line); border-radius: 16px;
    padding: 18px 20px; box-shadow: 0 2px 10px rgba(20,60,40,.04);
    animation: fadeUp .5s ease both;
}
.card-title { font-size: 13px; font-weight: 700; color: var(--green-dark); margin-bottom: 12px; }
.bar-row { margin: 0 0 16px; }
.bar-head {
    display: flex; justify-content: space-between; gap: 12px;
    font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 6px;
}
.bar-head span:last-child { color: var(--green-dark); font-weight: 800; white-space: nowrap; }
.bar-track { height: 10px; border-radius: 999px; background: #E8EFEA; overflow: hidden; }
.bar-fill {
    height: 100%; border-radius: 999px; transform-origin: left center;
    background: linear-gradient(90deg, var(--green), var(--green-mid));
    animation: growX .9s ease both;
}
.bar-sub { font-size: 11px; color: var(--muted); margin-top: 5px; }
.pill {
    display: inline-block; padding: 3px 11px; border-radius: 999px;
    font-size: 12px; font-weight: 600; margin: 2px 6px 2px 0;
}
.pill-done { background: #E3F3EA; color: #075B32; }
.pill-prog { background: #FBF3DF; color: #8A6A1F; }
.pill-none { background: #EEF1EF; color: #6F7F76; }

.profile { display: flex; align-items: center; gap: 16px; }
.avatar {
    width: 56px; height: 56px; border-radius: 50%; flex: 0 0 56px;
    background: linear-gradient(135deg, var(--green-dark), var(--green-mid));
    color: #fff; font-weight: 800; font-size: 19px;
    display: flex; align-items: center; justify-content: center;
    border: 2px solid var(--gold);
}
.profile-name { font-size: 20px; font-weight: 800; color: var(--green-dark); }
.profile-meta { font-size: 13px; color: var(--muted); margin-top: 2px; }

.welcome {
    background: #fff; border: 1px solid var(--line); border-radius: 18px;
    padding: 28px 30px; border-top: 4px solid var(--gold);
    box-shadow: 0 6px 24px rgba(20,60,40,.06); animation: fadeUp .6s ease both;
}
.welcome h3 { margin: 0 0 6px; color: var(--green-dark); font-size: 22px; font-weight: 800; }
.welcome p { color: var(--muted); margin: 0 0 14px; font-size: 14px; }
.steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
@media (max-width: 800px) { .steps { grid-template-columns: 1fr; } }
.step { background: #F7FAF8; border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.step b { color: var(--green-dark); display: block; margin-bottom: 4px; font-size: 14px; }
.step span { color: var(--muted); font-size: 12.5px; }

/* ---------- Streamlit widgets ---------- */
button[data-baseweb="tab"] { font-weight: 650; color: var(--muted); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--green-dark); }
div[data-baseweb="tab-highlight"] { background-color: var(--gold) !important; height: 3px; }

.stButton button, .stDownloadButton button {
    border-radius: 10px; font-weight: 650; background: #fff;
    border: 1px solid var(--green); color: var(--green-dark);
    transition: all .2s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
    background: var(--green); border-color: var(--green); color: #fff;
    transform: translateY(-2px);
}
.stDownloadButton button:hover p, .stButton button:hover p { color: #fff; }

[data-testid="stDataFrame"] {
    border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
}
[data-testid="stPlotlyChart"] {
    background: #fff; border: 1px solid var(--line); border-radius: 16px;
    padding: 6px; box-shadow: 0 2px 10px rgba(20,60,40,.04);
}
[data-testid="stExpander"] {
    background: #fff; border: 1px solid var(--line); border-radius: 12px;
}

#MainMenu, footer { visibility: hidden; }

@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes growX  { from { transform: scaleX(0); } to { transform: scaleX(1); } }

@media (max-width: 640px) {
    .block-container, [data-testid="stMainBlockContainer"] { padding-left: 1rem; padding-right: 1rem; }
    .app-title { font-size: 22px; }
}
@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ==================================================
# 2. UI HELPERS
# ==================================================

def esc(value):
    """Escape text for safe use inside HTML (also neutralises $ for Markdown math)."""
    return html_lib.escape(str(value)).replace("$", "&#36;")


def h(markup):
    """Flatten indented markup into one line so Markdown never turns it into a code block."""
    return "".join(line.strip() for line in markup.strip().splitlines())


def render_html(markup):
    st.markdown(h(markup), unsafe_allow_html=True)


def section(title):
    render_html(f'<div class="sec">{esc(title)}</div>')


def fmt_int(value):
    return f"{int(value):,}"


def fmt_pct(value, digits=1):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}f}%"


def kpi_card(label, value, sub="", gold=False):
    cls = "kpi kpi-gold" if gold else "kpi"
    return (
        f'<div class="{cls}"><div class="kpi-label">{esc(label)}</div>'
        f'<div class="kpi-value">{esc(value)}</div>'
        f'<div class="kpi-sub">{esc(sub)}</div></div>'
    )


def kpi_grid(cards):
    render_html('<div class="kpi-grid">' + "".join(cards) + "</div>")


def bar_row(label, pct, right_text, sub=""):
    width = max(0.0, min(100.0, float(pct)))
    return (
        f'<div class="bar-row"><div class="bar-head"><span>{esc(label)}</span>'
        f"<span>{esc(right_text)}</span></div>"
        f'<div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>'
        f'<div class="bar-sub">{esc(sub)}</div></div>'
    )


def status_pill(status):
    css = {"Completed": "pill-done", "In Progress": "pill-prog"}.get(status, "pill-none")
    return f'<span class="pill {css}">{esc(status)}</span>'


def show_table(df, **kwargs):
    """st.dataframe that works on both older and newer Streamlit width APIs."""
    kwargs.setdefault("hide_index", True)
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except Exception:
        st.dataframe(df, use_container_width=True, **kwargs)


def _accepts_width(func):
    """True when this Streamlit version's function has the newer `width` argument."""
    try:
        return "width" in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def show_chart(fig):
    """st.plotly_chart that works on both older and newer Streamlit width APIs."""
    config = {"displayModeBar": False}
    if _accepts_width(st.plotly_chart):
        try:
            st.plotly_chart(fig, width="stretch", config=config)
            return
        except Exception:
            pass
    st.plotly_chart(fig, use_container_width=True, config=config)


def pct_column(label):
    return st.column_config.ProgressColumn(
        label, min_value=0, max_value=100, format="%.0f%%"
    )


def csv_download(data):
    return data.to_csv(index=False).encode("utf-8-sig")


def find_logo():
    """Find the company logo next to app.py (or in the working directory)."""
    try:
        bases = [Path(__file__).resolve().parent, Path.cwd()]
    except NameError:
        bases = [Path.cwd()]
    for base in bases:
        exact = base / LOGO_FILE
        if exact.exists():
            return exact
        for candidate in sorted(base.glob("*.png")):
            if "bawani" in candidate.name.lower():
                return candidate
    return None


# ---------- charts (Plotly, one consistent look) ----------

def style_figure(fig, title=None, height=360, legend=False):
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT_STACK, size=13, color=INK),
        title=dict(
            text=title or "",
            x=0,
            xanchor="left",
            font=dict(size=15, color=DARK_GREEN),
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=12, r=16, t=56 if title else 18, b=14),
        height=height,
        showlegend=legend,
        colorway=PALETTE,
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT_STACK, size=13)),
    )
    if legend:
        fig.update_layout(
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0
            )
        )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, showline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showline=False)
    return fig


def shorten(text, limit=46):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def fig_hbar(labels, values, title=None, percent=False, decimals=0, colors=None):
    """Horizontal ranked bar chart. First item is drawn at the top."""
    labels = [str(x) for x in labels]
    values = [float(v) for v in values]
    suffix = "%" if percent else ""
    texts = [f"{v:,.{decimals}f}{suffix}" for v in values]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=[shorten(x) for x in labels],
            orientation="h",
            marker=dict(color=colors or GREEN),
            text=texts,
            textposition="outside",
            cliponaxis=False,
            customdata=labels,
            hovertemplate="%{customdata}<br><b>%{x:,.1f}" + suffix + "</b><extra></extra>",
        )
    )
    style_figure(fig, title, height=max(250, 36 * len(labels) + 90))
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    if percent:
        fig.update_xaxes(range=[0, 112], ticksuffix="%")
    else:
        top = max(values) if values else 1
        fig.update_xaxes(range=[0, top * 1.18 if top > 0 else 1])
    return fig


def fig_donut(labels, values, title=None, center_label="records"):
    total = int(sum(values))
    fig = go.Figure(
        go.Pie(
            labels=list(labels),
            values=[float(v) for v in values],
            hole=0.68,
            sort=False,
            direction="clockwise",
            marker=dict(
                colors=[STATUS_COLORS.get(x, MUTED) for x in labels],
                line=dict(color="white", width=3),
            ),
            textinfo="percent",
            hovertemplate="%{label}<br>%{value:,.0f} (%{percent})<extra></extra>",
        )
    )
    style_figure(fig, title, height=380, legend=True)
    fig.add_annotation(
        text=f"<b>{total:,}</b><br><span style='font-size:12px'>{esc(center_label)}</span>",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=24, color=DARK_GREEN),
    )
    return fig


def fig_line(x, y, title=None, suffix="", decimals=0):
    x = [str(v) for v in x]
    y = [None if pd.isna(v) else float(v) for v in y]
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line=dict(color=GREEN, width=3),
            marker=dict(size=9, color="white", line=dict(color=GREEN, width=2.5)),
            fill="tozeroy",
            fillcolor="rgba(8,120,62,0.07)",
            hovertemplate="%{x}<br><b>%{y:,.1f}" + suffix + "</b><extra></extra>",
        )
    )
    style_figure(fig, title, height=300)
    fig.update_xaxes(type="category")
    fig.update_yaxes(rangemode="tozero", ticksuffix=suffix)
    return fig


def fig_grouped_hbar(frame, category, series, value, title=None, suffix=""):
    """One bar group per category, one colour per series (e.g. per period)."""
    fig = go.Figure()
    for i, name in enumerate(list(dict.fromkeys(frame[series]))):
        part = frame[frame[series] == name]
        fig.add_trace(
            go.Bar(
                name=str(name),
                x=[float(v) for v in part[value]],
                y=[shorten(v, 34) for v in part[category]],
                orientation="h",
                marker=dict(color=PALETTE[i % len(PALETTE)]),
                hovertemplate="%{y}<br>" + str(name) + ": <b>%{x:,.1f}" + suffix + "</b><extra></extra>",
            )
        )
    n_rows = frame[category].nunique()
    style_figure(fig, title, height=max(300, 34 * n_rows * max(1, frame[series].nunique()) + 100), legend=True)
    fig.update_layout(barmode="group")
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    fig.update_xaxes(ticksuffix=suffix)
    return fig


# ==================================================
# 3. REPORT READING AND VALIDATION
# ==================================================

# Column names are matched after lower-casing and removing every character
# that is not a letter or digit, so "Percent Completed", "percent_completed"
# and "PERCENT COMPLETED" are all the same column.

EMAIL_ALIASES = ["email", "emailaddress", "learneremail", "useremail", "workemail"]

SUMMARY_ALIASES = {
    "email": EMAIL_ALIASES,
    "name": ["name", "fullname", "learnername", "employeename", "displayname"],
    "department": ["department", "dept", "departmentname"],
    "days": ["daysloggedin", "dayslogin", "loggedindays", "activedays"],
    "views": ["courseviews", "views", "totalcourseviews"],
    "completions": ["coursecompletions", "completions", "totalcompletions", "coursescompleted"],
    "hours": ["hoursviewed", "totalhoursviewed", "learninghours", "hours"],
}

DETAIL_ALIASES = {
    "email": EMAIL_ALIASES,
    "title": ["contentname", "coursename", "coursetitle", "contenttitle", "title"],
    "type": ["contenttype", "type"],
    "id": ["contentid", "courseid"],
    "percent": [
        "percentcompleted", "percentcomplete", "completionpercentage",
        "percentagecompleted", "progress", "completion",
    ],
    "completed_at": [
        "completedatpstpdt", "completedat", "completiondate",
        "completedon", "completeddate",
    ],
}


def norm_col(name):
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def find_col(columns, aliases):
    """Return the first real column whose normalised name matches an alias."""
    lookup = {norm_col(c): c for c in columns}
    for alias in aliases:
        if alias in lookup:
            return lookup[alias]
    return None


def _decode_text(raw):
    """Decode CSV bytes. Returns (text, note_or_None)."""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16"), None
    try:
        return raw.decode("utf-8-sig"), None
    except UnicodeDecodeError:
        return (
            raw.decode("latin-1"),
            "The file is not UTF-8, so it was read as Latin-1. "
            "Arabic text may not display correctly; re-export as UTF-8 if needed.",
        )


def _read_csv_grid(raw):
    """Read a CSV as a raw grid of text (no header guessing). Returns (frame, notes)."""
    text, note = _decode_text(raw)
    lines = [ln for ln in text.splitlines() if ln.strip()][:40]
    counts = {d: sum(ln.count(d) for ln in lines) for d in [",", ";", "\t", "|"]}
    delimiter = max(counts, key=counts.get) if max(counts.values()) > 0 else ","
    rows = [
        row
        for row in csv.reader(io.StringIO(text), delimiter=delimiter)
        if any(str(cell).strip() for cell in row)
    ]
    if not rows:
        raise ValueError("The file is empty.")
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    notes = [("info", note)] if note else []
    return pd.DataFrame(rows, dtype=object), notes


def _read_excel_grids(raw, filename):
    """Yield every sheet of an Excel workbook as a raw grid."""
    engine = "xlrd" if filename.lower().endswith(".xls") else "openpyxl"
    workbook = pd.ExcelFile(io.BytesIO(raw), engine=engine)
    for sheet in workbook.sheet_names:
        grid = workbook.parse(sheet, header=None, dtype=object)
        grid = grid.dropna(how="all").dropna(axis=1, how="all")
        if not grid.empty:
            yield sheet, grid.reset_index(drop=True)


def _promote_header(grid, key_aliases):
    """
    Turn a raw grid into a table. If key_aliases is given, the header row is the
    first of the top 25 rows containing one of them (this skips title lines that
    some exports put above the real header). Returns None when none is found.
    """
    header_row = 0
    if key_aliases:
        header_row = None
        for idx in range(min(25, len(grid))):
            cells = {norm_col(c) for c in grid.iloc[idx].tolist() if pd.notna(c)}
            if cells & set(key_aliases):
                header_row = idx
                break
        if header_row is None:
            return None

    names, seen = [], {}
    for pos, cell in enumerate(grid.iloc[header_row].tolist()):
        label = "" if pd.isna(cell) else str(cell).strip()
        label = label or f"Unnamed {pos + 1}"
        seen[label] = seen.get(label, 0) + 1
        names.append(label if seen[label] == 1 else f"{label} ({seen[label]})")

    table = grid.iloc[header_row + 1:].copy()
    table.columns = names
    return table.dropna(how="all").reset_index(drop=True)


@st.cache_data(show_spinner=False, max_entries=12)
def parse_report_bytes(raw, filename, require_email):
    """
    Parse an uploaded CSV/Excel report into a table of text/objects.
    Returns (table, notes). Raises ValueError with a readable message.
    """
    lower = filename.lower()
    key_aliases = EMAIL_ALIASES if require_email else None
    notes = []

    try:
        if lower.endswith((".csv", ".txt")):
            grid, notes = _read_csv_grid(raw)
            table = _promote_header(grid, key_aliases)
            sheets_checked = ["the file"]
        elif lower.endswith((".xlsx", ".xlsm", ".xls")):
            table, sheets_checked = None, []
            for sheet, grid in _read_excel_grids(raw, filename):
                sheets_checked.append(f"sheet '{sheet}'")
                table = _promote_header(grid, key_aliases)
                if table is not None:
                    if len(sheets_checked) > 1:
                        notes.append(("info", f"Data was read from sheet '{sheet}'."))
                    break
        else:
            raise ValueError("Unsupported file type. Please upload a .csv, .xlsx or .xls file.")
    except ValueError:
        raise
    except ImportError as error:
        raise ValueError(
            f"A required library is missing for this file type ({error}). "
            "Check that requirements.txt includes openpyxl and xlrd."
        )
    except Exception as error:
        raise ValueError(
            "The file could not be read. It may be corrupted or not a real "
            f"CSV/Excel file ({type(error).__name__})."
        )

    if table is None:
        raise ValueError(
            "No 'Email' column was found in " + ", ".join(sheets_checked or ["the file"])
            + ". Check that this is the correct LinkedIn Learning report."
        )
    if table.empty:
        raise ValueError("The report has a header row but no data rows.")
    return table, notes


def load_report(upload, label, require_email, problems):
    """Parse one uploaded file. Errors are collected in `problems`, never silent."""
    if upload is None:
        return None, []
    try:
        return parse_report_bytes(upload.getvalue(), upload.name, require_email)
    except ValueError as error:
        problems.append(f"{label} ({upload.name}): {error}")
        return None, []


# ==================================================
# 4. DATA PREPARATION
# ==================================================

def clean_text(series):
    return (
        series.fillna("").astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def clean_email(series):
    return series.fillna("").astype(str).str.replace(r"\s+", "", regex=True).str.lower()


def to_number(series):
    """Counts: tolerate thousands separators and blanks; negatives become 0."""
    text = series.fillna("").astype(str).str.replace(",", "", regex=False)
    return pd.to_numeric(text, errors="coerce").fillna(0).clip(lower=0)


def parse_progress(series):
    """
    Convert 'Percent Completed' to 0-100. Handles '45%', '45', '45,5' and Excel
    percentage cells that arrive as fractions (0.45). Returns (values, notes).
    """
    notes = []
    text = series.fillna("").astype(str).str.strip()
    blank = text.eq("") | text.str.lower().isin(["nan", "none", "nat"])
    has_percent_sign = text.str.contains("%", regex=False)
    cleaned = text.str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
    values = pd.to_numeric(cleaned, errors="coerce")

    unreadable = values.isna() & ~blank
    if unreadable.any():
        notes.append((
            "warning",
            f"{int(unreadable.sum()):,} 'Percent Completed' values could not be read "
            "and were counted as 0%.",
        ))
    if blank.any():
        notes.append((
            "info",
            f"{int(blank.sum()):,} blank 'Percent Completed' values were counted as 0%.",
        ))

    known = values.dropna()
    if not has_percent_sign.any() and len(known) and 0 < known.max() <= 1:
        values = values * 100
        notes.append((
            "info",
            "'Percent Completed' values were all between 0 and 1, so they were read "
            "as fractions and converted to percentages.",
        ))

    if (values > 100).any():
        notes.append((
            "info",
            f"{int((values > 100).sum()):,} progress values above 100% were capped at 100%.",
        ))
    return values.fillna(0).clip(0, 100), notes


def parse_hours(value):
    """Hours as decimal hours. Accepts numbers, 'H:MM:SS', 'MM:SS' and Excel time cells."""
    try:
        if value is None or pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        pass

    if isinstance(value, (pd.Timedelta, timedelta)):
        return float(value.total_seconds() / 3600)
    if isinstance(value, dtime):
        return value.hour + value.minute / 60 + value.second / 3600
    if isinstance(value, (int, float, np.integer, np.floating)):
        return max(0.0, float(value))

    text = str(value).strip()
    try:
        if ":" in text:
            parts = [float(p) for p in text.split(":")]
            if len(parts) == 3:
                return max(0.0, parts[0] + parts[1] / 60 + parts[2] / 3600)
            if len(parts) == 2:  # kept from the original app: MM:SS
                return max(0.0, parts[0] / 60 + parts[1] / 3600)
            return 0.0
        if "," in text and "." in text:
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
        return max(0.0, float(text))
    except (ValueError, TypeError):
        return 0.0


def get_status(progress):
    if progress >= 100:
        return "Completed"
    if progress > 0:
        return "In Progress"
    return "Not Started"


def normalize_title(text):
    """Comparable form of a course title: case, accents, '&', punctuation, spacing."""
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def email_to_name(email):
    local = str(email).split("@")[0]
    return re.sub(r"[._\-]+", " ", local).title() or str(email)


def prepare_summary(data):
    """Validate and standardise Learner Summary. Returns (table, notes)."""
    notes = []
    df = data.copy()
    col = {key: find_col(df.columns, aliases) for key, aliases in SUMMARY_ALIASES.items()}

    if col["email"] is None:
        raise ValueError(
            "Learner Summary has no Email column. Columns found: "
            + ", ".join(map(str, df.columns[:12]))
        )

    out = pd.DataFrame(index=df.index)
    out["Email"] = clean_email(df[col["email"]])

    blank = out["Email"].eq("")
    if blank.any():
        notes.append((
            "warning",
            f"{int(blank.sum()):,} Learner Summary rows had no email and were ignored.",
        ))
    out = out[~blank].copy()
    df = df.loc[out.index]

    no_at = ~out["Email"].str.contains("@", regex=False)
    if no_at.any():
        notes.append((
            "warning",
            f"{int(no_at.sum()):,} Learner Summary emails do not look like email addresses.",
        ))

    if col["name"]:
        out["Name"] = clean_text(df[col["name"]])
    else:
        out["Name"] = ""
        notes.append(("warning", "Learner Summary has no Name column; names were built from emails."))
    missing_name = out["Name"].eq("")
    out.loc[missing_name, "Name"] = out.loc[missing_name, "Email"].map(email_to_name)

    if col["department"]:
        out["Department"] = clean_text(df[col["department"]]).replace("", "Not Specified")
    else:
        out["Department"] = "Not Specified"
        notes.append(("warning", "Learner Summary has no Department column; all employees are 'Not Specified'."))

    for key, target, label in [
        ("days", "Days Logged In", "Days Logged In"),
        ("views", "Course Views", "Course Views"),
        ("completions", "Course Completions", "Course Completions"),
    ]:
        if col[key]:
            out[target] = to_number(df[col[key]])
        else:
            out[target] = 0.0
            notes.append(("warning", f"Learner Summary has no '{label}' column; it is shown as 0."))

    if col["hours"]:
        out["Learning Hours"] = df[col["hours"]].map(parse_hours)
    else:
        out["Learning Hours"] = 0.0
        notes.append(("warning", "Learner Summary has no 'Hours Viewed' column; learning hours are shown as 0."))

    duplicates = int(out.duplicated("Email", keep="last").sum())
    if duplicates:
        notes.append((
            "info",
            f"{duplicates:,} duplicate employee rows were removed (the last row per email is kept).",
        ))
    out = out.drop_duplicates("Email", keep="last").reset_index(drop=True)
    return out, notes


def prepare_detail(data, summary):
    """Validate and standardise Learner Detail (one row per employee and course)."""
    notes = []
    df = data.copy()
    col = {key: find_col(df.columns, aliases) for key, aliases in DETAIL_ALIASES.items()}

    if col["email"] is None:
        raise ValueError("Learner Detail has no Email column.")
    if col["title"] is None:
        raise ValueError("Learner Detail has no course title column (expected 'Content Name').")
    if col["percent"] is None:
        raise ValueError(
            "Learner Detail has no 'Percent Completed' column. Mandatory and course "
            "completion cannot be calculated without it."
        )

    out = pd.DataFrame(index=df.index)
    out["Email"] = clean_email(df[col["email"]])
    out["Content Name"] = clean_text(df[col["title"]])
    progress, progress_notes = parse_progress(df[col["percent"]])
    out["Progress"] = progress
    notes.extend(progress_notes)

    if col["completed_at"]:
        out["Completed At"] = (
            clean_text(df[col["completed_at"]])
            .str.replace(r"\s00:00:00$", "", regex=True)
        )
    else:
        out["Completed At"] = ""

    if col["type"]:
        kind = clean_text(df[col["type"]]).str.casefold()
        is_course = kind.eq("course")
        if is_course.any():
            skipped = int((~is_course).sum())
            if skipped:
                notes.append(("info", f"{skipped:,} non-course rows (videos, paths, etc.) were excluded."))
            out = out[is_course]
        else:
            notes.append((
                "warning",
                "No rows were marked as Content Type 'Course', so all rows were used.",
            ))

    unusable = out["Email"].eq("") | out["Content Name"].eq("")
    if unusable.any():
        notes.append(("warning", f"{int(unusable.sum()):,} Learner Detail rows had no email or course title and were ignored."))
        out = out[~unusable]

    content_id = clean_text(df.loc[out.index, col["id"]]) if col["id"] else pd.Series("", index=out.index)
    out["Course Key"] = content_id.where(content_id.ne(""), out["Content Name"].str.lower())
    out["Title Key"] = out["Content Name"].map(normalize_title)
    out["Status"] = out["Progress"].map(get_status)

    mismatch = out["Completed At"].ne("") & out["Progress"].lt(100)
    if mismatch.any():
        notes.append((
            "warning",
            f"{int(mismatch.sum()):,} course rows have a completion date but progress below 100%. "
            "They are counted by their Percent Completed value.",
        ))

    out = out.sort_values("Progress", ascending=False)
    duplicates = int(out.duplicated(["Email", "Course Key"], keep="first").sum())
    if duplicates:
        notes.append((
            "info",
            f"{duplicates:,} duplicate employee/course rows were removed (highest progress kept).",
        ))
    out = out.drop_duplicates(["Email", "Course Key"], keep="first")

    known = out["Email"].isin(set(summary["Email"]))
    if (~known).any():
        notes.append((
            "warning",
            f"{int((~known).sum()):,} course rows belong to {out.loc[~known, 'Email'].nunique():,} "
            "emails that are not in Learner Summary and were excluded.",
        ))
    out = out[known]

    lookup = summary.set_index("Email")
    out["Name"] = out["Email"].map(lookup["Name"])
    out["Department"] = out["Email"].map(lookup["Department"])

    cols = ["Email", "Name", "Department", "Content Name", "Course Key",
            "Title Key", "Progress", "Status", "Completed At"]
    return out[cols].reset_index(drop=True), notes


def enrich_summary(summary, detail):
    """Add per-employee course counts and the Active flag to the summary."""
    flags = detail.assign(
        _done=detail["Status"].eq("Completed").astype(int),
        _prog=detail["Status"].eq("In Progress").astype(int),
    )
    stats = flags.groupby("Email").agg(
        **{
            "Courses Enrolled": ("Course Key", "size"),
            "Courses Completed": ("_done", "sum"),
            "Courses In Progress": ("_prog", "sum"),
            "Avg Progress": ("Progress", "mean"),
        }
    )
    out = summary.merge(stats, how="left", left_on="Email", right_index=True)
    for column in ["Courses Enrolled", "Courses Completed", "Courses In Progress"]:
        out[column] = out[column].fillna(0).astype(int)
    out["Avg Progress"] = out["Avg Progress"].fillna(0.0)

    with_progress = set(detail.loc[detail["Progress"] > 0, "Email"])
    out["Active"] = (
        out["Learning Hours"].gt(0)
        | out["Course Views"].gt(0)
        | out["Days Logged In"].gt(0)
        | out["Email"].isin(with_progress)
    )
    return out


# ==================================================
# 5. ANALYTICS
# ==================================================

# ---------- mandatory program ----------

def match_mask(title_keys, configured_title, mode):
    cfg = normalize_title(configured_title)
    if not cfg:
        return pd.Series(False, index=title_keys.index)
    if mode == MATCH_CONTAINS:
        return title_keys.str.contains(cfg, regex=False)
    return title_keys.eq(cfg)


def compute_mandatory(employees, courses, configured, mode):
    """
    One row per employee with status/progress for each configured mandatory course.
    Completion is verified against actual course rows (Learner Detail), never
    against the Course Completions count in Learner Summary.
    """
    base = (
        employees[["Email", "Name", "Department"]]
        .drop_duplicates("Email")
        .reset_index(drop=True)
    )
    total = len(configured)
    done = pd.Series(0, index=base.index)
    touched = pd.Series(0.0, index=base.index)

    for i, title in enumerate(configured, start=1):
        mask = match_mask(courses["Title Key"], title, mode)
        best = courses.loc[mask].groupby("Email")["Progress"].max()
        progress = base["Email"].map(best).fillna(0.0).astype(float)
        base[f"Progress {i}"] = progress
        base[f"Course {i}"] = progress.map(get_status)
        done = done + progress.ge(100).astype(int)
        touched = touched + progress

    base["Completed Courses"] = done
    base["Program Progress"] = done / total * 100
    base["Is Complete"] = done.eq(total)
    base["Mandatory Status"] = np.where(
        base["Is Complete"], "Complete", np.where(touched > 0, "In Progress", "Not Started")
    )
    return base


def mandatory_display(frame, configured):
    """Rename internal columns to the real course titles for tables and CSV export."""
    out = pd.DataFrame(
        {"Employee": frame["Name"], "Email": frame["Email"], "Department": frame["Department"]}
    )
    for i, title in enumerate(configured, start=1):
        out[title] = frame[f"Course {i}"]
        out[f"{title} (%)"] = frame[f"Progress {i}"].round(0)
    out["Completed Courses"] = (
        frame["Completed Courses"].astype(str) + " / " + str(len(configured))
    )
    out["Program Progress"] = frame["Program Progress"].round(0)
    out["Mandatory Status"] = frame["Mandatory Status"]
    return out


def mandatory_department_table(frame, configured):
    rows = []
    for department, part in frame.groupby("Department"):
        row = {
            "Department": department,
            "Employees": len(part),
            "Fully Complete": int(part["Is Complete"].sum()),
            "Completion Rate": float(part["Is Complete"].mean() * 100),
        }
        for i, title in enumerate(configured, start=1):
            row[f"{title} (% done)"] = float(part[f"Course {i}"].eq("Completed").mean() * 100)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("Completion Rate", ascending=False).reset_index(drop=True)


def mandatory_diagnostics(courses, configured, mode):
    """Show which real course titles each configured title matched (or nearly matched)."""
    names = dict(zip(courses["Title Key"], courses["Content Name"]))
    rows = []
    for i, title in enumerate(configured, start=1):
        mask = match_mask(courses["Title Key"], title, mode)
        matched = sorted(courses.loc[mask, "Content Name"].unique())
        suggestion = ""
        if not matched:
            close = difflib.get_close_matches(
                normalize_title(title), list(names.keys()), n=3, cutoff=0.55
            )
            suggestion = " | ".join(names[key] for key in close)
        rows.append({
            "Mandatory Course": f"{i}. {title}",
            "Matched Titles in Learner Detail": " | ".join(matched) if matched else "NO MATCH",
            "Learners With a Record": int(courses.loc[mask, "Email"].nunique()),
            "Did You Mean": suggestion,
        })
    return pd.DataFrame(rows)


def optional_summary(courses, mandatory, configured, mode):
    """
    Optional learning = every course that is not one of the mandatory courses.
    Returns (per-employee table for people who finished mandatory, optional records).
    """
    mask = pd.Series(False, index=courses.index)
    for title in configured:
        mask = mask | match_mask(courses["Title Key"], title, mode)
    optional = courses[~mask]

    flags = optional.assign(
        _done=optional["Status"].eq("Completed").astype(int),
        _prog=optional["Status"].eq("In Progress").astype(int),
    )
    per_employee = flags.groupby("Email").agg(
        **{
            "Optional Enrolled": ("Course Key", "size"),
            "Optional Completed": ("_done", "sum"),
            "Optional In Progress": ("_prog", "sum"),
        }
    )
    table = mandatory.merge(per_employee, how="left", left_on="Email", right_index=True)
    for column in per_employee.columns:
        table[column] = table[column].fillna(0).astype(int)
    return table, optional


# ---------- monthly history ----------

HISTORY_COLUMNS = [
    "Period", "Record Type", "Email", "Name", "Department", "Course Key",
    "Course Name", "Progress", "Status", "Learning Hours", "Course Views",
    "Course Completions", "Days Logged In",
]
HISTORY_NUMERIC = ["Progress", "Learning Hours", "Course Views", "Course Completions", "Days Logged In"]
PERIOD_FORMATS = ["%b %Y", "%B %Y", "%b-%Y", "%B-%Y", "%Y-%m", "%m/%Y", "%Y/%m", "%b %y", "%B %y", "%b, %Y", "%B, %Y"]


def parse_period(text):
    text = str(text).strip().replace("Sept ", "Sep ")
    for fmt in PERIOD_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def normalize_period(text):
    parsed = parse_period(text)
    return parsed.strftime("%b %Y") if parsed else str(text).strip()


def ordered_periods(series):
    """Periods in calendar order (not alphabetical). Unrecognised labels go last."""
    unique = list(dict.fromkeys(series.astype(str)))
    known = sorted((p for p in unique if parse_period(p)), key=parse_period)
    unknown = [p for p in unique if not parse_period(p)]
    return known + unknown


def build_current_history(summary, detail, period):
    employees = pd.DataFrame({
        "Period": period,
        "Record Type": "Employee",
        "Email": summary["Email"],
        "Name": summary["Name"],
        "Department": summary["Department"],
        "Course Key": "",
        "Course Name": "",
        "Progress": np.nan,
        "Status": "",
        "Learning Hours": summary["Learning Hours"],
        "Course Views": summary["Course Views"],
        "Course Completions": summary["Course Completions"],
        "Days Logged In": summary["Days Logged In"],
    })
    courses = pd.DataFrame({
        "Period": period,
        "Record Type": "Course",
        "Email": detail["Email"],
        "Name": detail["Name"],
        "Department": detail["Department"],
        "Course Key": detail["Course Key"],
        "Course Name": detail["Content Name"],
        "Progress": detail["Progress"],
        "Status": detail["Status"],
        "Learning Hours": np.nan,
        "Course Views": np.nan,
        "Course Completions": np.nan,
        "Days Logged In": np.nan,
    })
    return pd.concat([courses, employees], ignore_index=True)[HISTORY_COLUMNS]


def normalize_archive(data):
    """
    Validate an uploaded archive. Accepts the new format (with 'Record Type')
    and archives made by the previous version of this app (course rows only).
    """
    notes = []
    df = data.copy()
    lookup = {norm_col(c): c for c in df.columns}
    df = df.rename(columns={
        lookup[norm_col(c)]: c for c in HISTORY_COLUMNS if norm_col(c) in lookup
    })

    missing = [c for c in ("Period", "Email") if c not in df.columns]
    if missing:
        raise ValueError(
            "This does not look like a Learning Hub archive (missing: "
            + ", ".join(missing) + "). Upload the CSV downloaded from the Monthly History tab."
        )

    for column in HISTORY_COLUMNS:
        if column not in df.columns:
            df[column] = np.nan if column in HISTORY_NUMERIC else ""
    df = df[HISTORY_COLUMNS].copy()

    for column in ["Period", "Record Type", "Name", "Department", "Course Key", "Course Name", "Status"]:
        df[column] = clean_text(df[column])
    df["Email"] = clean_email(df["Email"])
    df["Period"] = df["Period"].map(normalize_period)
    for column in HISTORY_NUMERIC:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    record_type = df["Record Type"].str.title()
    df["Record Type"] = record_type.where(record_type.isin(["Course", "Employee"]), "Course")
    df.loc[df["Department"].eq(""), "Department"] = "Not Specified"

    unusable = df["Email"].eq("") | df["Period"].eq("")
    is_course = df["Record Type"].eq("Course")
    df["Course Key"] = df["Course Key"].where(
        df["Course Key"].ne(""), df["Course Name"].str.lower()
    )
    unusable = unusable | (is_course & df["Course Key"].eq(""))
    if unusable.any():
        notes.append((
            "warning",
            f"{int(unusable.sum()):,} archive rows were missing a period, email or course and were ignored.",
        ))
    df = df[~unusable].copy()

    is_course = df["Record Type"].eq("Course")
    df.loc[is_course, "Progress"] = df.loc[is_course, "Progress"].fillna(0).clip(0, 100)
    df.loc[is_course, "Status"] = df.loc[is_course, "Progress"].map(get_status)
    if df.empty:
        raise ValueError("The archive contains no usable records.")
    return df.reset_index(drop=True), notes


def merge_history(archive, current, period):
    """Add the current period. A re-uploaded period replaces its earlier records."""
    notes = []
    if archive is not None and len(archive):
        replaced = int(archive["Period"].eq(period).sum())
        if replaced:
            notes.append((
                "info",
                f"The archive already had {replaced:,} records for {period}. "
                "They were replaced by the current upload.",
            ))
        combined = pd.concat([archive[archive["Period"].ne(period)], current], ignore_index=True)
    else:
        combined = current.copy()
    combined = combined.drop_duplicates(
        ["Period", "Record Type", "Email", "Course Key"], keep="last"
    )
    return combined.reset_index(drop=True), notes


def period_overview(history, configured, mode):
    courses = history[history["Record Type"].eq("Course")]
    employees = history[history["Record Type"].eq("Employee")]
    rows = []
    for period in ordered_periods(history["Period"]):
        c = courses[courses["Period"].eq(period)]
        e = employees[employees["Period"].eq(period)]
        headcount = e["Email"].nunique() if len(e) else c["Email"].nunique()
        completed = int(c["Status"].eq("Completed").sum())
        row = {
            "Period": period,
            "Employees": int(headcount),
            "Course Records": len(c),
            "Completed": completed,
            "Completion Rate": completed / len(c) * 100 if len(c) else np.nan,
            "Avg Progress": float(c["Progress"].mean()) if len(c) else np.nan,
            "Learning Hours": float(e["Learning Hours"].sum()) if e["Learning Hours"].notna().any() else np.nan,
            "Mandatory Complete": np.nan,
        }
        if configured and len(c):
            roster = e if len(e) else c
            matrix = compute_mandatory(
                roster, c.assign(**{"Title Key": c["Course Name"].map(normalize_title)}),
                configured, mode,
            )
            row["Mandatory Complete"] = float(matrix["Is Complete"].mean() * 100)
        rows.append(row)
    return pd.DataFrame(rows)


def department_by_period(history):
    courses = history[history["Record Type"].eq("Course")]
    if courses.empty:
        return pd.DataFrame(columns=["Period", "Department", "Course Records", "Completed", "Completion Rate", "Avg Progress"])
    flags = courses.assign(_done=courses["Status"].eq("Completed").astype(int))
    table = flags.groupby(["Period", "Department"], as_index=False).agg(
        **{
            "Course Records": ("Course Key", "size"),
            "Completed": ("_done", "sum"),
            "Avg Progress": ("Progress", "mean"),
        }
    )
    table["Completion Rate"] = table["Completed"] / table["Course Records"] * 100
    order = {p: i for i, p in enumerate(ordered_periods(table["Period"]))}
    table["_o"] = table["Period"].map(order)
    return table.sort_values(["_o", "Department"]).drop(columns="_o").reset_index(drop=True)


# ==================================================
# 6. SIDEBAR, DATA LOADING, FILTERS, KPIs
# ==================================================

REPORT_TYPES = ["csv", "xlsx", "xls"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

with st.sidebar:
    render_html(
        '<div class="side-brand">LEARNING HUB</div>'
        '<div class="side-sub">Al Bawani | Learning &amp; Development</div>'
    )

    render_html('<div class="side-label">LinkedIn Learning reports</div>')
    summary_file = st.file_uploader("Learner Summary", type=REPORT_TYPES, key="summary")
    detail_file = st.file_uploader("Learner Detail", type=REPORT_TYPES, key="detail")
    group_file = st.file_uploader("Group Summary (optional)", type=REPORT_TYPES, key="group")
    recommendation_file = st.file_uploader(
        "Recommendation Summary (optional)", type=REPORT_TYPES, key="recommendation"
    )

    render_html('<div class="side-label">Reporting period</div>')
    today = date.today()
    month_col, year_col = st.columns(2)
    with month_col:
        report_month = st.selectbox("Month", MONTHS, index=today.month - 1, key="report_month")
    with year_col:
        years = list(range(today.year - 3, today.year + 2))
        report_year = st.selectbox("Year", years, index=years.index(today.year), key="report_year")
    period = f"{report_month} {report_year}"

    render_html('<div class="side-label">Mandatory courses</div>')
    mandatory_inputs = []
    for i in range(1, 4):
        default = DEFAULT_MANDATORY_COURSES[i - 1] if i <= len(DEFAULT_MANDATORY_COURSES) else ""
        title = st.text_input(
            f"Mandatory course {i}",
            value=default,
            placeholder="Official course title",
            key=f"course_{i}",
        )
        mandatory_inputs.append(title.strip())
    match_mode = st.radio(
        "Title matching",
        [MATCH_EXACT, MATCH_CONTAINS],
        key="match_mode",
        help=(
            "Exact title ignores capitals, punctuation and extra spaces. "
            "'Title contains text' also accepts longer titles that include what you typed "
            "(useful when LinkedIn adds a version suffix)."
        ),
    )

    render_html('<div class="side-label">Historical archive</div>')
    archive_file = st.file_uploader("Previous tracking archive (CSV)", type=["csv"], key="archive")
    st.caption(
        "This app does not save data. Download the archive after each period "
        "and upload it again next month."
    )


# ---------- configured mandatory courses (blank and repeated titles removed) ----------

configured_courses = []
_seen_titles = set()
for _title in mandatory_inputs:
    _key = normalize_title(_title)
    if _key and _key not in _seen_titles:
        configured_courses.append(_title)
        _seen_titles.add(_key)
repeated_titles = len([t for t in mandatory_inputs if t]) - len(configured_courses)


# ---------- header ----------

logo_path = find_logo()
head_logo, head_title = st.columns([1.5, 5], vertical_alignment="center")
with head_logo:
    if logo_path is not None:
        st.image(str(logo_path), width=200)
    else:
        render_html('<div class="app-title">AL BAWANI</div>')
with head_title:
    render_html(
        '<div class="eyebrow">People Development</div>'
        '<div class="app-title">Learning &amp; Development Dashboard</div>'
    )
render_html('<div class="gold-rule"></div>')


# ---------- load and validate uploads ----------

problems = []
summary_raw, summary_load_notes = load_report(summary_file, "Learner Summary", True, problems)
detail_raw, detail_load_notes = load_report(detail_file, "Learner Detail", True, problems)
group_data, _ = load_report(group_file, "Group Summary", False, problems)
recommendation_data, _ = load_report(recommendation_file, "Recommendation Summary", False, problems)

for message in problems:
    st.error(message)

if summary_raw is None or detail_raw is None:
    if not problems:
        render_html(
            '<div class="welcome"><h3>Welcome to the Learning Hub</h3>'
            "<p>Upload the two LinkedIn Learning reports in the sidebar to open the dashboard.</p>"
            '<div class="steps">'
            '<div class="step"><b>1. Upload reports</b><span>Learner Summary and Learner Detail (CSV or Excel).</span></div>'
            '<div class="step"><b>2. Set the period</b><span>Choose the reporting month and year.</span></div>'
            '<div class="step"><b>3. Add mandatory courses</b><span>Enter the three official course titles.</span></div>'
            "</div></div>"
        )
    st.stop()

try:
    summary, summary_notes = prepare_summary(summary_raw)
    detail, detail_notes = prepare_detail(detail_raw, summary)
except ValueError as error:
    st.error(str(error))
    st.stop()

data_notes = summary_load_notes + summary_notes + detail_load_notes + detail_notes
if repeated_titles:
    data_notes.append(("warning", "A mandatory course title was entered more than once; duplicates were ignored."))
if recommendation_data is not None and recommendation_data.empty:
    data_notes.append(("info", "The Recommendation Summary has no records."))

summary = enrich_summary(summary, detail)

if summary.empty:
    st.error("Learner Summary contains no employees after validation.")
    st.stop()


# ---------- mandatory program (computed once, filtered later) ----------

mandatory_all = None
if configured_courses:
    mandatory_all = compute_mandatory(summary, detail, configured_courses, match_mode)


# ---------- status strip ----------

if configured_courses:
    program_chip = f"<b>{len(configured_courses)} of 3</b> mandatory courses set"
else:
    program_chip = "Mandatory courses <b>not set</b>"
render_html(
    '<div class="chips">'
    f'<span class="chip chip-gold">Period <b>{esc(period)}</b></span>'
    f'<span class="chip"><b>{len(summary):,}</b> employees</span>'
    f'<span class="chip"><b>{len(detail):,}</b> course records</span>'
    f'<span class="chip">{program_chip}</span>'
    "</div>"
)

if data_notes:
    has_warning = any(level == "warning" for level, _ in data_notes)
    with st.expander(f"Data quality notes ({len(data_notes)})", expanded=has_warning):
        for level, message in data_notes:
            prefix = "**Check:** " if level == "warning" else ""
            st.markdown(f"- {prefix}{message}")


# ---------- filters ----------

section("Filters")
filter_dept, filter_search = st.columns([1, 1.4])
with filter_dept:
    selected_department = st.selectbox(
        "Department",
        ["All Departments"] + sorted(summary["Department"].unique().tolist()),
        key="filter_department",
    )
with filter_search:
    employee_search = st.text_input(
        "Search employee", placeholder="Name or email", key="filter_search"
    ).strip()

filtered_summary = summary.copy()
if selected_department != "All Departments":
    filtered_summary = filtered_summary[filtered_summary["Department"] == selected_department]
if employee_search:
    filtered_summary = filtered_summary[
        filtered_summary["Name"].str.contains(employee_search, case=False, regex=False)
        | filtered_summary["Email"].str.contains(employee_search, case=False, regex=False)
    ]

filtered_emails = set(filtered_summary["Email"])
filtered_detail = detail[detail["Email"].isin(filtered_emails)].copy()
mandatory_view = (
    mandatory_all[mandatory_all["Email"].isin(filtered_emails)].copy()
    if mandatory_all is not None
    else None
)

if filtered_summary.empty:
    st.warning("No employees match the current filters.")
    st.stop()

st.caption(f"Showing {len(filtered_summary):,} of {len(summary):,} employees.")


# ---------- KPI cards ----------

total_employees = len(filtered_summary)
active_learners = int(filtered_summary["Active"].sum())
total_hours = float(filtered_summary["Learning Hours"].sum())
total_views = int(filtered_summary["Course Views"].sum())
reported_completions = int(filtered_summary["Course Completions"].sum())
detail_completed = int(filtered_detail["Status"].eq("Completed").sum())
avg_progress = float(filtered_detail["Progress"].mean()) if len(filtered_detail) else np.nan

if mandatory_view is not None:
    complete_count = int(mandatory_view["Is Complete"].sum())
    incomplete_count = total_employees - complete_count
    mandatory_rate_text = fmt_pct(complete_count / total_employees * 100)
    mandatory_sub = f"{complete_count:,} of {total_employees:,} employees"
    incomplete_text = f"{incomplete_count:,}"
    incomplete_sub = "need to finish the mandatory courses"
else:
    mandatory_rate_text, mandatory_sub = "—", "Set the mandatory courses in the sidebar"
    incomplete_text, incomplete_sub = "—", "Set the mandatory courses in the sidebar"

kpi_grid([
    kpi_card("Total Employees", fmt_int(total_employees), selected_department if selected_department != "All Departments" else "All departments"),
    kpi_card("Active Learners", fmt_int(active_learners), f"{active_learners / total_employees * 100:.0f}% of employees"),
    kpi_card("Learning Hours", f"{total_hours:,.1f} h", f"{total_hours / total_employees:.1f} h per employee"),
    kpi_card("Course Views", fmt_int(total_views), "Learner Summary"),
    kpi_card("Course Completions", fmt_int(reported_completions), f"Reported by LinkedIn · {detail_completed:,} in Learner Detail"),
    kpi_card("Avg Course Progress", fmt_pct(avg_progress), f"{len(filtered_detail):,} course records"),
    kpi_card("Mandatory Completion", mandatory_rate_text, mandatory_sub, gold=True),
    kpi_card("Incomplete Mandatory", incomplete_text, incomplete_sub, gold=True),
])
st.caption(
    "Active learner: any viewing time, course view, login or course progress in the reports. "
    "Mandatory completion is verified against course rows in Learner Detail."
)


# ---------- department statistics (shared by Overview) ----------

department_stats = filtered_summary.groupby("Department", as_index=False).agg(
    Employees=("Email", "nunique"),
    Active=("Active", "sum"),
    Views=("Course Views", "sum"),
    Completions=("Course Completions", "sum"),
    Hours=("Learning Hours", "sum"),
)
department_stats["Per Employee"] = department_stats["Completions"] / department_stats["Employees"]
progress_by_department = filtered_detail.groupby("Department")["Progress"].mean()
department_stats["Avg Progress"] = department_stats["Department"].map(progress_by_department).fillna(0.0)
if mandatory_view is not None:
    complete_by_department = mandatory_view.groupby("Department")["Is Complete"].mean() * 100
    department_stats["Mandatory Complete"] = (
        department_stats["Department"].map(complete_by_department).fillna(0.0)
    )


# ==================================================
# 7. TABS
# ==================================================

tab_overview, tab_employees, tab_courses, tab_mandatory, tab_history = st.tabs([
    "Overview",
    "Employee Tracking",
    "Course Analytics",
    "Mandatory Program",
    "Monthly History",
])


# ==================================================
# TAB 1: OVERVIEW
# ==================================================

DEPARTMENT_METRICS = {
    "Course completions": ("Completions", False, 0),
    "Completions per employee": ("Per Employee", False, 1),
    "Learning hours": ("Hours", False, 1),
    "Average progress": ("Avg Progress", True, 0),
}

with tab_overview:
    left, right = st.columns([3, 2])

    with left:
        section("Department Performance")
        metric_label = st.radio(
            "Metric",
            list(DEPARTMENT_METRICS),
            horizontal=True,
            label_visibility="collapsed",
            key="department_metric",
        )
        metric_column, metric_is_percent, metric_decimals = DEPARTMENT_METRICS[metric_label]
        ranked = department_stats.sort_values(metric_column, ascending=False).head(15)
        show_chart(fig_hbar(
            ranked["Department"], ranked[metric_column],
            percent=metric_is_percent, decimals=metric_decimals,
        ))

    with right:
        section("Course Status")
        order = ["Completed", "In Progress", "Not Started"]
        status_counts = filtered_detail["Status"].value_counts().reindex(order, fill_value=0)
        if status_counts.sum() > 0:
            show_chart(fig_donut(order, status_counts.tolist(), center_label="course records"))
        else:
            st.info("No course records for the current filters.")

    left, right = st.columns([3, 2])

    with left:
        section("Most Popular Courses")
        if len(filtered_detail):
            popular = (
                filtered_detail.groupby("Content Name")["Email"].nunique()
                .sort_values(ascending=False).head(8)
            )
            show_chart(fig_hbar(popular.index, popular.values, decimals=0))
        else:
            st.info("No course activity available.")

    with right:
        section("Mandatory Snapshot")
        if mandatory_view is not None:
            bars = []
            for i, title in enumerate(configured_courses, start=1):
                done = int(mandatory_view[f"Course {i}"].eq("Completed").sum())
                bars.append(bar_row(
                    title, done / total_employees * 100,
                    f"{done:,} / {total_employees:,}",
                    f"{done / total_employees * 100:.0f}% of employees completed",
                ))
            render_html('<div class="card"><div class="card-title">Completion by course</div>' + "".join(bars) + "</div>")
        else:
            st.info("Enter the mandatory course titles in the sidebar to see compliance here.")

    section("Department Summary")
    summary_columns = {
        "Department": "Department",
        "Employees": "Employees",
        "Active": "Active Learners",
        "Views": "Course Views",
        "Completions": "Completions",
        "Hours": "Learning Hours",
        "Avg Progress": "Avg Progress",
    }
    if mandatory_view is not None:
        summary_columns["Mandatory Complete"] = "Mandatory Complete"
    dept_table = department_stats[list(summary_columns)].rename(columns=summary_columns)
    dept_table["Learning Hours"] = dept_table["Learning Hours"].round(1)
    config = {"Avg Progress": pct_column("Avg Progress")}
    if mandatory_view is not None:
        config["Mandatory Complete"] = pct_column("Mandatory Complete")
    show_table(dept_table.sort_values("Employees", ascending=False), column_config=config)

    if group_data is not None and not group_data.empty:
        section("LinkedIn Group Summary")
        show_table(group_data)


# ==================================================
# TAB 2: EMPLOYEE TRACKING
# ==================================================

with tab_employees:
    section("Employee Directory")

    directory = filtered_summary[[
        "Name", "Email", "Department", "Courses Enrolled", "Courses Completed",
        "Courses In Progress", "Avg Progress", "Learning Hours",
        "Course Views", "Course Completions", "Days Logged In",
    ]].copy()
    if mandatory_view is not None:
        directory = directory.merge(
            mandatory_view[["Email", "Mandatory Status", "Completed Courses"]],
            on="Email", how="left",
        )
        directory = directory.rename(columns={"Completed Courses": "Mandatory Done"})
    directory["Learning Hours"] = directory["Learning Hours"].round(1)
    directory["Avg Progress"] = directory["Avg Progress"].round(0)

    show_table(
        directory.sort_values("Name"),
        column_config={"Avg Progress": pct_column("Avg Progress")},
    )
    st.download_button(
        "Download employee directory",
        csv_download(directory),
        file_name="al_bawani_employee_directory.csv",
        mime="text/csv",
        key="dl_directory",
    )

    section("Employee Profile")
    name_lookup = dict(zip(filtered_summary["Email"], filtered_summary["Name"]))
    email_options = sorted(name_lookup, key=lambda e: (name_lookup[e].casefold(), e))
    selected_email = st.selectbox(
        "Select employee",
        email_options,
        format_func=lambda e: f"{name_lookup[e]}  —  {e}",
        key="profile_employee",
    )
    employee = filtered_summary[filtered_summary["Email"] == selected_email].iloc[0]
    employee_courses = filtered_detail[filtered_detail["Email"] == selected_email]

    initials = "".join(part[0] for part in employee["Name"].split()[:2]).upper() or "?"
    render_html(
        '<div class="card"><div class="profile">'
        f'<div class="avatar">{esc(initials)}</div>'
        f'<div><div class="profile-name">{esc(employee["Name"])}</div>'
        f'<div class="profile-meta">{esc(employee["Email"])} · {esc(employee["Department"])}</div></div>'
        "</div></div>"
    )

    kpi_grid([
        kpi_card("Courses Enrolled", fmt_int(employee["Courses Enrolled"])),
        kpi_card("Completed", fmt_int(employee["Courses Completed"]), "Learner Detail"),
        kpi_card("In Progress", fmt_int(employee["Courses In Progress"])),
        kpi_card("Avg Progress", fmt_pct(employee["Avg Progress"] if employee["Courses Enrolled"] else np.nan)),
        kpi_card("Learning Hours", f"{employee['Learning Hours']:.1f} h"),
        kpi_card("Course Views", fmt_int(employee["Course Views"])),
        kpi_card("Completions", fmt_int(employee["Course Completions"]), "Reported by LinkedIn"),
        kpi_card("Days Logged In", fmt_int(employee["Days Logged In"])),
    ])

    if mandatory_view is not None:
        record = mandatory_all[mandatory_all["Email"] == selected_email].iloc[0]
        pills = "".join(
            f'<div style="margin-bottom:6px">{status_pill(record[f"Course {i}"])}'
            f'<b style="font-size:13px">{esc(title)}</b>'
            f'<span style="color:#6F7F76;font-size:12px"> · {record[f"Progress {i}"]:.0f}%</span></div>'
            for i, title in enumerate(configured_courses, start=1)
        )
        render_html(
            '<div class="card"><div class="card-title">Mandatory training · '
            f'{esc(record["Mandatory Status"])} ({int(record["Completed Courses"])} of {len(configured_courses)})</div>'
            + pills + "</div>"
        )

    section("Courses")
    if employee_courses.empty:
        st.info("No course records found for this employee.")
    else:
        course_columns = ["Content Name", "Progress", "Status"]
        if employee_courses["Completed At"].ne("").any():
            course_columns.append("Completed At")
        show_table(
            employee_courses[course_columns].sort_values("Progress", ascending=False),
            column_config={"Progress": pct_column("Progress")},
        )


# ==================================================
# TAB 3: COURSE ANALYTICS
# ==================================================

RANK_OPTIONS = ["Learners", "Completions", "Completion rate (min. 3 learners)"]

with tab_courses:
    section("Course Analytics")

    if filtered_detail.empty:
        st.info("No course activity available.")
    else:
        course_stats = filtered_detail.groupby("Content Name").agg(
            Learners=("Email", "nunique"),
            **{"Avg Progress": ("Progress", "mean")},
        )
        completed_learners = (
            filtered_detail[filtered_detail["Status"] == "Completed"]
            .groupby("Content Name")["Email"].nunique()
        )
        course_stats["Completed"] = completed_learners.reindex(course_stats.index).fillna(0).astype(int)
        course_stats["Completion Rate"] = course_stats["Completed"] / course_stats["Learners"] * 100
        course_stats = course_stats.reset_index()

        controls_a, controls_b = st.columns([2, 3])
        with controls_a:
            rank_by = st.radio("Rank courses by", RANK_OPTIONS, key="course_rank")
        with controls_b:
            course_query = st.text_input("Find a course", placeholder="Part of the course title", key="course_query").strip()

        view = course_stats
        if course_query:
            view = view[view["Content Name"].str.contains(course_query, case=False, regex=False)]

        if rank_by == "Learners":
            ranked = view.sort_values(["Learners", "Content Name"], ascending=[False, True]).head(15)
            chart_values, chart_percent = ranked["Learners"], False
        elif rank_by == "Completions":
            ranked = view.sort_values(["Completed", "Content Name"], ascending=[False, True]).head(15)
            chart_values, chart_percent = ranked["Completed"], False
        else:
            ranked = view[view["Learners"] >= 3].sort_values(
                ["Completion Rate", "Learners"], ascending=[False, False]
            ).head(15)
            chart_values, chart_percent = ranked["Completion Rate"], True

        if ranked.empty:
            st.info("No courses match these settings.")
        else:
            show_chart(fig_hbar(ranked["Content Name"], chart_values, percent=chart_percent))

        section("All Courses")
        table = view.sort_values("Learners", ascending=False)[
            ["Content Name", "Learners", "Completed", "Completion Rate", "Avg Progress"]
        ].rename(columns={"Content Name": "Course"})
        show_table(
            table,
            column_config={
                "Completion Rate": pct_column("Completion Rate"),
                "Avg Progress": pct_column("Avg Progress"),
            },
        )
        st.caption("Completion rate = learners who completed the course ÷ learners with a record for it.")

    if recommendation_data is not None:
        section("Recommended Courses")
        if recommendation_data.empty:
            st.caption("No recommendation records in this report.")
        else:
            show_table(recommendation_data)


# ==================================================
# TAB 4: MANDATORY PROGRAM
# ==================================================

with tab_mandatory:
    section("Mandatory Learning Program")

    if mandatory_view is None:
        st.info(
            "Mandatory course titles are not set yet. Enter the official titles "
            "in the sidebar (Mandatory courses)."
        )
    else:
        if len(configured_courses) < 3:
            st.warning(
                f"Only {len(configured_courses)} of 3 mandatory courses are set. "
                "Completion is calculated on the courses entered."
            )

        # ---- is every title found in Learner Detail? ----
        diagnostics = mandatory_diagnostics(detail, configured_courses, match_mode)
        unmatched = diagnostics[diagnostics["Matched Titles in Learner Detail"] == "NO MATCH"]
        if not unmatched.empty:
            st.warning(
                f"{len(unmatched)} mandatory title(s) match no course in Learner Detail, "
                "so every employee shows as not started for them. "
                "Open 'Course name match check' below to see close matches."
            )

        total_view = len(mandatory_view)
        complete_total = int(mandatory_view["Is Complete"].sum())
        in_progress_total = int(mandatory_view["Mandatory Status"].eq("In Progress").sum())
        not_started_total = int(mandatory_view["Mandatory Status"].eq("Not Started").sum())

        kpi_grid([
            kpi_card("Completion Rate", fmt_pct(complete_total / total_view * 100), "All mandatory courses done", gold=True),
            kpi_card("Fully Complete", fmt_int(complete_total), f"of {total_view:,} employees"),
            kpi_card("In Progress", fmt_int(in_progress_total), "Started, not finished"),
            kpi_card("Not Started", fmt_int(not_started_total), "No progress yet"),
        ])

        # ---- per-course completion ----
        left, right = st.columns([1, 1])
        with left:
            section("Completion by Course")
            bars = []
            for i, title in enumerate(configured_courses, start=1):
                statuses = mandatory_view[f"Course {i}"]
                done = int(statuses.eq("Completed").sum())
                started = int(statuses.eq("In Progress").sum())
                bars.append(bar_row(
                    title, done / total_view * 100, f"{done:,} / {total_view:,}",
                    f"{started:,} in progress · {total_view - done - started:,} not started",
                ))
            render_html('<div class="card">' + "".join(bars) + "</div>")

        with right:
            section("Completion by Department")
            department_mandatory = mandatory_department_table(mandatory_view, configured_courses)
            show_chart(fig_hbar(
                department_mandatory["Department"].head(15),
                department_mandatory["Completion Rate"].head(15),
                percent=True,
            ))

        department_config = {"Completion Rate": pct_column("Completion Rate")}
        for title in configured_courses:
            department_config[f"{title} (% done)"] = pct_column(f"{title} (% done)")
        show_table(department_mandatory, column_config=department_config)

        # ---- employee matrix ----
        section("Employee Completion Matrix")
        view_choice = st.radio(
            "Show",
            ["All employees", "Incomplete only", "Complete only"],
            horizontal=True,
            key="mandatory_view_choice",
        )
        matrix_source = mandatory_view
        if view_choice == "Incomplete only":
            matrix_source = mandatory_view[~mandatory_view["Is Complete"]]
        elif view_choice == "Complete only":
            matrix_source = mandatory_view[mandatory_view["Is Complete"]]

        matrix = mandatory_display(
            matrix_source.sort_values(["Mandatory Status", "Name"]), configured_courses
        )
        matrix_config = {"Program Progress": pct_column("Program Progress")}
        for title in configured_courses:
            matrix_config[f"{title} (%)"] = pct_column(f"{title} (%)")
        st.caption(f"{len(matrix):,} employees shown.")
        show_table(matrix, column_config=matrix_config)

        full_export = mandatory_display(mandatory_view.sort_values("Name"), configured_courses)
        incomplete_export = mandatory_display(
            mandatory_view[~mandatory_view["Is Complete"]].sort_values(["Department", "Name"]),
            configured_courses,
        )
        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            st.download_button(
                "Download mandatory tracking",
                csv_download(full_export),
                file_name="al_bawani_mandatory_tracking.csv",
                mime="text/csv",
                key="dl_mandatory_all",
            )
        with dl2:
            st.download_button(
                "Download incomplete employees",
                csv_download(incomplete_export),
                file_name="al_bawani_mandatory_incomplete.csv",
                mime="text/csv",
                key="dl_mandatory_incomplete",
            )
        with dl3:
            st.download_button(
                "Download department rates",
                csv_download(department_mandatory.round(1)),
                file_name="al_bawani_mandatory_departments.csv",
                mime="text/csv",
                key="dl_mandatory_departments",
            )

        with st.expander("Course name match check"):
            st.caption(
                "Shows which course titles in Learner Detail each mandatory title matched. "
                "If a title shows NO MATCH, copy the suggested title or switch 'Title matching' "
                "in the sidebar."
            )
            show_table(diagnostics)

        # ---- optional learning after mandatory ----
        section("Optional Learning")
        optional_table, optional_records = optional_summary(
            detail, mandatory_view, configured_courses, match_mode
        )
        eligible = optional_table[optional_table["Is Complete"]]
        engaged = eligible[eligible["Optional Enrolled"] > 0]
        early = optional_table[~optional_table["Is Complete"] & (optional_table["Optional Enrolled"] > 0)]

        kpi_grid([
            kpi_card("Finished Mandatory", fmt_int(len(eligible)), "Ready for optional courses"),
            kpi_card("Taking Optional Courses", fmt_int(len(engaged)), f"{len(engaged) / len(eligible) * 100:.0f}% of those who finished" if len(eligible) else "No one has finished yet"),
            kpi_card("Optional Completions", fmt_int(eligible["Optional Completed"].sum()), "Among those who finished"),
            kpi_card("Optional Before Mandatory", fmt_int(len(early)), "Started optional first"),
        ])

        if eligible.empty:
            st.info("Optional course activity will appear here once employees finish the mandatory courses.")
        else:
            eligible_records = optional_records[optional_records["Email"].isin(set(eligible["Email"]))]
            left, right = st.columns([3, 2])
            with left:
                if eligible_records.empty:
                    st.info("Employees who finished the mandatory courses have no optional course records yet.")
                else:
                    top_optional = (
                        eligible_records.groupby("Content Name")["Email"].nunique()
                        .sort_values(ascending=False).head(10)
                    )
                    show_chart(fig_hbar(top_optional.index, top_optional.values, title="Top optional courses"))
            with right:
                render_html(
                    '<div class="card"><div class="card-title">How this is counted</div>'
                    '<div style="font-size:13px;color:#6F7F76;line-height:1.6">'
                    "Optional courses are every course that is not one of the mandatory titles. "
                    "The chart and table below only include employees who completed all mandatory courses."
                    "</div></div>"
                )

            optional_view = eligible[[
                "Name", "Email", "Department", "Optional Enrolled",
                "Optional Completed", "Optional In Progress",
            ]].rename(columns={"Name": "Employee"}).sort_values(
                ["Optional Completed", "Optional Enrolled"], ascending=False
            )
            show_table(optional_view)
            st.download_button(
                "Download optional learning report",
                csv_download(optional_view),
                file_name="al_bawani_optional_learning.csv",
                mime="text/csv",
                key="dl_optional",
            )


# ==================================================
# TAB 5: MONTHLY HISTORY
# ==================================================

with tab_history:
    section("Monthly Learning History")

    with st.expander("How history is stored"):
        st.markdown(
            "- This app **does not save data**. Uploaded reports stay in memory for your session only, "
            "and Streamlit Community Cloud storage is temporary.\n"
            "- Your history is the **archive CSV** you download below. Keep it safe and upload it next month.\n"
            "- Re-uploading the same period replaces that period's earlier records.\n"
            "- For permanent, shared history, ask IT for a company-approved store "
            "(for example a managed SQL database or a restricted SharePoint library) "
            "so access and retention follow company policy."
        )

    # ---- build history: archive (optional) + current upload ----
    history_notes = []
    archive = None
    if archive_file is not None:
        try:
            archive_raw, archive_load_notes = parse_report_bytes(archive_file.getvalue(), archive_file.name, True)
            archive, archive_notes = normalize_archive(archive_raw)
            history_notes.extend(archive_load_notes + archive_notes)
        except ValueError as error:
            st.error(f"Archive ({archive_file.name}): {error} The archive was ignored.")
            archive = None

    current_history = build_current_history(summary, detail, period)
    history, merge_notes = merge_history(archive, current_history, period)
    history_notes.extend(merge_notes)
    for level, message in history_notes:
        (st.warning if level == "warning" else st.info)(message)

    periods = ordered_periods(history["Period"])
    history_courses = history[history["Record Type"] == "Course"]
    overview = period_overview(history, configured_courses, match_mode)

    kpi_grid([
        kpi_card("Periods Tracked", fmt_int(len(periods)), f"{periods[0]} → {periods[-1]}" if len(periods) > 1 else periods[0]),
        kpi_card("Course Records", fmt_int(len(history_courses))),
        kpi_card("Employees Tracked", fmt_int(history["Email"].nunique())),
        kpi_card("Latest Completion Rate", fmt_pct(overview["Completion Rate"].iloc[-1]), f"Period {overview['Period'].iloc[-1]}", gold=True),
    ])

    section("Period Comparison")
    show_table(
        overview,
        column_config={
            "Completion Rate": pct_column("Completion Rate"),
            "Avg Progress": pct_column("Avg Progress"),
            "Mandatory Complete": pct_column("Mandatory Complete"),
            "Learning Hours": st.column_config.NumberColumn("Learning Hours", format="%.1f"),
        },
    )
    st.caption(
        "Completion rate = completed course records ÷ all course records in that period. "
        "Learning hours and mandatory completion need archive data from the new version of this app "
        "(older archives only contain course records)."
    )

    if len(periods) < 2:
        st.info("Trend charts and comparisons appear once the archive holds two or more periods.")
    else:
        section("Trends")
        left, right = st.columns(2)
        with left:
            show_chart(fig_line(overview["Period"], overview["Completed"], title="Completed courses"))
        with right:
            show_chart(fig_line(overview["Period"], overview["Avg Progress"], title="Average course progress", suffix="%"))

        left, right = st.columns(2)
        with left:
            if overview["Learning Hours"].notna().any():
                show_chart(fig_line(overview["Period"], overview["Learning Hours"], title="Learning hours"))
            else:
                st.info("Learning hours are not in the uploaded archive.")
        with right:
            if configured_courses and overview["Mandatory Complete"].notna().any():
                show_chart(fig_line(overview["Period"], overview["Mandatory Complete"], title="Mandatory completion", suffix="%"))
            else:
                st.info("Set the mandatory courses to see the mandatory completion trend.")

        # ---- compare two periods ----
        section("Compare Two Periods")
        pick_a, pick_b = st.columns(2)
        with pick_a:
            period_a = st.selectbox("From", periods, index=len(periods) - 2, key="compare_a")
        with pick_b:
            period_b = st.selectbox("To", periods, index=len(periods) - 1, key="compare_b")

        dept_history = department_by_period(history)
        part_a = dept_history[dept_history["Period"] == period_a].set_index("Department")
        part_b = dept_history[dept_history["Period"] == period_b].set_index("Department")
        compare = pd.DataFrame({
            f"Completed ({period_a})": part_a["Completed"],
            f"Completed ({period_b})": part_b["Completed"],
            f"Avg Progress ({period_a})": part_a["Avg Progress"],
            f"Avg Progress ({period_b})": part_b["Avg Progress"],
        })
        compare["Change in Completed"] = compare.iloc[:, 1].fillna(0) - compare.iloc[:, 0].fillna(0)
        compare["Change in Avg Progress (pts)"] = compare.iloc[:, 3] - compare.iloc[:, 2]
        compare = compare.round(1).reset_index().rename(columns={"index": "Department"})
        if period_a == period_b:
            st.info("Choose two different periods to compare.")
        else:
            show_table(compare)

        # ---- department performance over time ----
        section("Department Performance by Period")
        metric_choice = st.radio(
            "Metric", ["Completion Rate", "Avg Progress"], horizontal=True,
            label_visibility="collapsed", key="history_dept_metric",
        )
        recent_periods = periods[-4:]
        dept_recent = dept_history[dept_history["Period"].isin(recent_periods)]
        if dept_recent.empty:
            st.info("No course records to compare.")
        else:
            show_chart(fig_grouped_hbar(dept_recent, "Department", "Period", metric_choice, suffix="%"))
            st.caption("The chart shows the latest four periods.")

    # ---- one course over time ----
    if len(periods) >= 2 and not history_courses.empty:
        section("Course Completion Trend")
        course_names = (
            history_courses.groupby("Course Name").size().sort_values(ascending=False).index.tolist()
        )
        chosen_course = st.selectbox("Course", ["All courses"] + course_names, key="history_course")
        course_rows = history_courses if chosen_course == "All courses" else history_courses[history_courses["Course Name"] == chosen_course]
        rows = []
        for p in periods:
            part = course_rows[course_rows["Period"] == p]
            rows.append({
                "Period": p,
                "Learners": part["Email"].nunique(),
                "Completed": int(part["Status"].eq("Completed").sum()),
                "Completion Rate": float(part["Status"].eq("Completed").mean() * 100) if len(part) else np.nan,
                "Avg Progress": float(part["Progress"].mean()) if len(part) else np.nan,
            })
        course_trend = pd.DataFrame(rows)
        left, right = st.columns([3, 2])
        with left:
            show_chart(fig_line(course_trend["Period"], course_trend["Completion Rate"], title="Completion rate", suffix="%"))
        with right:
            show_table(course_trend, column_config={
                "Completion Rate": pct_column("Completion Rate"),
                "Avg Progress": pct_column("Avg Progress"),
            })

    # ---- one employee over time ----
    section("Employee Progress Over Time")
    people = history.drop_duplicates("Email").set_index("Email")["Name"].to_dict()
    people_options = sorted(people, key=lambda e: (str(people[e]).casefold(), e))
    chosen_email = st.selectbox(
        "Employee",
        people_options,
        format_func=lambda e: f"{people[e] or email_to_name(e)}  —  {e}",
        key="history_employee",
    )
    person_courses = history_courses[history_courses["Email"] == chosen_email]
    person_employee = history[(history["Email"] == chosen_email) & (history["Record Type"] == "Employee")]
    person_rows = []
    for p in periods:
        c = person_courses[person_courses["Period"] == p]
        e = person_employee[person_employee["Period"] == p]
        if c.empty and e.empty:
            continue
        person_rows.append({
            "Period": p,
            "Courses": len(c),
            "Completed": int(c["Status"].eq("Completed").sum()),
            "Avg Progress": float(c["Progress"].mean()) if len(c) else np.nan,
            "Learning Hours": float(e["Learning Hours"].sum()) if len(e) and e["Learning Hours"].notna().any() else np.nan,
        })
    person_timeline = pd.DataFrame(person_rows)
    if person_timeline.empty:
        st.info("No history for this employee.")
    else:
        if len(person_timeline) >= 2:
            left, right = st.columns(2)
            with left:
                show_chart(fig_line(person_timeline["Period"], person_timeline["Completed"], title="Completed courses"))
            with right:
                show_chart(fig_line(person_timeline["Period"], person_timeline["Avg Progress"], title="Average progress", suffix="%"))
        show_table(person_timeline, column_config={"Avg Progress": pct_column("Avg Progress")})
        show_table(
            person_courses[person_courses["Email"] == chosen_email][
                ["Period", "Course Name", "Progress", "Status"]
            ].sort_values(["Period", "Course Name"]),
            column_config={"Progress": pct_column("Progress")},
        )

    # ---- archive download ----
    section("Historical Archive")
    st.download_button(
        "Download / update historical archive",
        csv_download(history[HISTORY_COLUMNS]),
        file_name="al_bawani_learning_history_archive.csv",
        mime="text/csv",
        key="dl_archive",
    )
    st.caption("Upload this file as the Previous tracking archive next month, together with the new reports.")


# ==================================================
# FOOTER
# ==================================================

st.divider()
render_html(
    '<div style="text-align:center;color:#89958E;font-size:11px;padding:10px;letter-spacing:.08em;">'
    "AL BAWANI | LEARNING &amp; DEVELOPMENT"
    "</div>"
)
