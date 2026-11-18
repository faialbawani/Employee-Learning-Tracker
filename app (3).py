"""
Al Bawani Learning Hub
LinkedIn Learning management dashboard (Streamlit).

Pages: Overview · Employee Access · Employee Profiles · Mandatory Program ·
       Course Analytics · Monthly History

Data rules
- LearnerManagement is the primary source for employee and login information.
- Login activity and course activity are tracked separately.
- Employees are matched across reports by Email, or by Unique User ID — never by name.
- Only rows whose Content Type is "Course" count as course completions.
- Missing values stay missing (shown as "—"); they are never silently converted to zero.
- Mandatory-course configuration lives in the browser session only; it is preserved
  through JSON export / import (no permanent storage is claimed).
"""

import html
import io
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Al Bawani | Learning Hub", page_icon="📚", layout="wide")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GREEN = "#08783E"
DARK = "#075B32"
GOLD = "#C6A45B"
MUTED = "#6B7A72"
INK = "#1D3327"
GREY = "#AAB5AE"

DEFAULT_PERIOD_START = date(2026, 10, 17)
DEFAULT_PERIOD_END = date(2026, 11, 16)

ALL_DEPTS = "All Departments"
NO_DEPT = "Not Specified"

LOGGED_IN = "Logged In"
NO_LOGIN = "No Login During Selected Period"
LOGIN_NA = "Login Data Not Available"
LOGIN_ORDER = [LOGGED_IN, NO_LOGIN, LOGIN_NA]

ACT_YES = "Course Activity"
ACT_NO = "No Course Activity"
ACT_NA = "Course Data Not Available"
ACTIVITY_ORDER = [ACT_YES, ACT_NO, ACT_NA]

COMPLETED = "Completed"
IN_PROGRESS = "In Progress"
NOT_STARTED = "Not Started"
UNKNOWN = "Unknown"
STATUS_ORDER = [COMPLETED, IN_PROGRESS, NOT_STARTED, UNKNOWN]
STATUS_RANK = {COMPLETED: 3, IN_PROGRESS: 2, NOT_STARTED: 1, UNKNOWN: 0}

NOT_CONFIGURED = "Mandatory Courses Not Configured"
CONFIGURED = "Configured"

PAGES = [
    "Overview",
    "Employee Access",
    "Employee Profiles",
    "Mandatory Program",
    "Course Analytics",
    "Monthly History",
]

REPORT_SPECS = [
    ("management", "LearnerManagement", "Employee and login information (primary source)"),
    ("summary", "LearnerSummary", "Employee-level learning metrics"),
    ("detail", "LearnerDetail", "Individual course and learning activity"),
    ("group", "GroupSummary", "Group-level analytics (optional)"),
    ("content", "ContentSummary", "Content-level analytics (optional)"),
    ("rec_summary", "RecommendationSummary", "Recommendation information (optional)"),
    ("rec_detail", "RecommendationDetail", "Recommendation information (optional)"),
]

LOGIN_COLORS = {LOGGED_IN: GREEN, NO_LOGIN: GOLD, LOGIN_NA: GREY}
ACTIVITY_COLORS = {ACT_YES: GREEN, ACT_NO: GOLD, ACT_NA: GREY}
STATUS_COLORS = {COMPLETED: GREEN, IN_PROGRESS: GOLD, NOT_STARTED: "#C9D3CD", UNKNOWN: "#8E9B94"}

_GREEN_CELL = "background-color:#E4F2E9;color:#075B32;font-weight:600"
_GOLD_CELL = "background-color:#FAF3E2;color:#7A5B17;font-weight:600"
_GREY_CELL = "background-color:#EFF2F0;color:#56645C;font-weight:600"
_RED_CELL = "background-color:#FBECEA;color:#9A3A30;font-weight:600"
CELL_STYLES = {
    LOGGED_IN: _GREEN_CELL,
    NO_LOGIN: _GOLD_CELL,
    LOGIN_NA: _GREY_CELL,
    ACT_YES: _GREEN_CELL,
    ACT_NO: _GOLD_CELL,
    ACT_NA: _GREY_CELL,
    COMPLETED: _GREEN_CELL,
    IN_PROGRESS: _GOLD_CELL,
    NOT_STARTED: _RED_CELL,
    UNKNOWN: _GREY_CELL,
    CONFIGURED: _GREEN_CELL,
    NOT_CONFIGURED: _GREY_CELL,
}

MISSING_TOKENS = {"", "-", "--", "—", "n/a", "na", "nan", "none", "null", "nat", "#n/a"}

EMAIL_CANDS = ["Email", "Email Address", "Work Email", "Primary Email", "E-mail", "Learner Email", "User Email"]
UID_CANDS = ["Unique User ID", "Unique User Id", "Unique ID", "User ID", "Employee ID", "Employee Number"]
NAME_CANDS = ["Name", "Full Name", "Learner Name", "Employee Name", "Learner"]
DEPT_CANDS = ["Department", "Dept", "Department Name", "Division", "Business Unit"]
TITLE_CANDS = ["Business Title", "Job Title"]

HISTORY_COLUMNS = [
    "Record Type", "Period", "Period Start", "Period End", "Email Key", "Employee Name", "Department",
    "Login Status", "Days Logged In", "Course Activity Status", "Courses Completed",
    "Course Key", "Course ID", "Course Name", "Content Type", "Progress", "Status",
    "Learning Hours", "Completed Date",
]

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {font-family: 'Inter', 'Segoe UI', sans-serif;}
.stApp {background:#FFFFFF; color:#1D3327;}
.block-container {padding-top:1.2rem; padding-bottom:2rem; max-width:1440px;}
[data-testid="stSidebar"] {background:#F6F9F7; border-right:1px solid #E3EBE5;}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {color:#075B32;}
h1, h2, h3, h4 {color:#17452F; letter-spacing:-0.2px;}
.ab-header {display:flex; align-items:flex-end; justify-content:space-between; gap:16px; flex-wrap:wrap;
            border-bottom:2px solid #C6A45B; padding-bottom:12px; margin-bottom:14px;}
.ab-eyebrow {font-size:11px; letter-spacing:2px; color:#C6A45B; font-weight:800; text-transform:uppercase;}
.ab-title {font-size:28px; font-weight:800; color:#075B32; line-height:1.2;}
.ab-subtitle {font-size:13px; color:#6B7A72;}
.ab-period {font-size:13px; color:#075B32; background:#EEF6F1; border:1px solid #D3E6DA; border-radius:999px;
            padding:6px 14px; font-weight:600; white-space:nowrap;}
.section-title {font-size:18px; font-weight:750; color:#17452F; margin:18px 0 10px; padding-left:10px;
                border-left:4px solid #C6A45B;}
.kpi-card {background:#FFFFFF; border:1px solid #E3EBE5; border-left:4px solid #08783E; border-radius:10px;
           padding:12px 14px; min-height:96px; box-shadow:0 2px 8px rgba(20,60,40,.04); margin-bottom:10px;}
.kpi-label {font-size:11.5px; color:#6B7A72; font-weight:700; text-transform:uppercase; letter-spacing:.4px;}
.kpi-value {font-size:26px; font-weight:800; color:#075B32; margin-top:4px; line-height:1.15;}
.kpi-sub {font-size:11.5px; color:#6B7A72; margin-top:2px;}
.notice {background:#FCFAF3; border:1px solid #EFE4C8; border-left:4px solid #C6A45B; border-radius:10px;
         padding:12px 16px; font-size:13px; color:#3B4A41; margin:2px 0 16px;}
.notice-title {font-weight:800; color:#075B32; font-size:14px; margin-bottom:2px;}
.notice-lead {font-weight:600; color:#17452F; margin-bottom:6px;}
.notice-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:6px 20px;}
.notice-grid b {color:#17452F;}
.employee-name {font-size:42px; font-weight:800; color:#075B32; line-height:1.1; margin:8px 0 4px; word-break:break-word;}
.employee-sub {font-size:16px; color:#6B7A72; margin-bottom:16px;}
.info-grid {display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px; margin-bottom:8px;}
.info-item {background:#F7FAF8; border:1px solid #E3EBE5; border-radius:8px; padding:10px 12px;}
.info-label {font-size:11px; color:#6B7A72; font-weight:700; text-transform:uppercase; letter-spacing:.4px;}
.info-value {font-size:15px; color:#1D3327; font-weight:600; margin-top:3px; word-break:break-word;}
.badge {display:inline-block; padding:3px 10px; border-radius:999px; font-size:12.5px;}
.ab-footer {text-align:center; color:#89958E; font-size:11px; padding:14px 0 4px; letter-spacing:1px;}
div[data-testid="stTabs"] button p {font-weight:650;}
.stButton button, .stDownloadButton button {border-radius:8px; font-weight:650;}
@media (max-width: 640px) {
  .employee-name {font-size:30px;}
  .ab-title {font-size:22px;}
  .kpi-value {font-size:22px;}
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def esc(value):
    """HTML-escape any value for safe use inside st.markdown(unsafe_allow_html=True)."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return html.escape(str(value))


def is_missing(value):
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def norm_col(name):
    return re.sub(r"[^a-z0-9]", "", str(name).casefold())


def find_col(df, candidates=(), prefixes=()):
    """Flexible column detection: exact match on normalised names first, then prefix match."""
    if df is None:
        return None
    lookup = {}
    for col in df.columns:
        lookup.setdefault(norm_col(col), col)
    for cand in candidates:
        key = norm_col(cand)
        if key in lookup:
            return lookup[key]
    for prefix in prefixes:
        pkey = norm_col(prefix)
        for key, col in lookup.items():
            if key.startswith(pkey):
                return col
    return None


def na_text(index):
    return pd.Series(pd.NA, index=index, dtype="string")


def na_float(index):
    return pd.Series(float("nan"), index=index, dtype="float64")


def na_dates(index):
    return pd.Series(pd.NaT, index=index, dtype="datetime64[ns]")


def clean_text(series):
    s = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    missing = s.str.casefold().isin(MISSING_TOKENS).fillna(True).astype(bool)
    return s.mask(missing | s.isna())


def text_or_na(df, col):
    return clean_text(df[col]) if col else na_text(df.index)


def to_object(series):
    """Object series with None for missing values (safe for element-wise parsing)."""
    values = [None if is_missing(v) else v for v in series.astype(object).tolist()]
    return pd.Series(values, index=series.index, dtype=object)


def parse_number(series):
    s = clean_text(series).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(to_object(s), errors="coerce").astype("float64")


def to_float(series):
    return pd.to_numeric(series, errors="coerce").astype("float64")


_HMS = re.compile(r"^(\d+):(\d{1,2})(?::(\d{1,2}(?:\.\d+)?))?$")


def _hours_value(value):
    if value is None:
        return float("nan")
    text = str(value).strip().replace(",", "")
    match = _HMS.match(text)
    if match:
        hours = float(match.group(1))
        minutes = float(match.group(2))
        seconds = float(match.group(3) or 0)
        return hours + minutes / 60 + seconds / 3600
    text = re.sub(r"\s*(h|hr|hrs|hour|hours)$", "", text, flags=re.IGNORECASE)
    try:
        return float(text)
    except ValueError:
        return float("nan")


def parse_hours(series):
    cleaned = to_object(clean_text(series))
    return pd.Series([_hours_value(v) for v in cleaned.tolist()], index=series.index, dtype="float64")


_TZ_SUFFIX = re.compile(r"\s*\(?\b(PST|PDT|UTC|GMT|AST|EST|EDT|CST|CDT)\b\)?\s*$", re.IGNORECASE)


def parse_dates(series):
    """Returns (datetime series, number of non-empty values that could not be parsed)."""
    cleaned = to_object(clean_text(series))
    cleaned = cleaned.map(lambda v: _TZ_SUFFIX.sub("", v) if isinstance(v, str) else v)
    if cleaned.notna().sum() == 0:
        return na_dates(series.index), 0
    try:
        out = pd.to_datetime(cleaned, errors="coerce", format="mixed", utc=True)
    except (TypeError, ValueError):
        out = pd.to_datetime(cleaned, errors="coerce", utc=True)
    out = out.dt.tz_localize(None)
    invalid = int((cleaned.notna() & out.isna()).sum())
    return out, invalid


def norm_title(value):
    """Careful normalisation for exact course-name matching (no fuzzy matching)."""
    if is_missing(value):
        return ""
    s = unicodedata.normalize("NFKC", str(value)).casefold()
    s = re.sub(r"[‐-―−]", "-", s)
    s = re.sub(r"[‘’‛`´]", "'", s)
    s = re.sub(r"[“”]", '"', s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def dept_key(value):
    """Normalises department naming conventions (case, spacing, '&' vs 'and', 'Department' suffix)."""
    if is_missing(value):
        return NO_DEPT.casefold()
    s = unicodedata.normalize("NFKC", str(value)).casefold().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^(department|dept) of ", "", s)
    s = re.sub(r" (department|dept)$", "", s)
    return s or NO_DEPT.casefold()


def canonical_departments(series):
    s = series.astype(object).where(series.notna(), NO_DEPT)
    s = s.map(lambda v: re.sub(r"\s+", " ", str(v)).strip() or NO_DEPT)
    keys = s.map(dept_key)

    def pick(variants):
        counts = variants.value_counts()
        # Most frequent spelling; ties prefer properly capitalised, then shorter names.
        ranked = sorted(counts.index, key=lambda v: (-counts[v], v == v.lower(), len(v), v))
        return ranked[0]

    best = s.groupby(keys).agg(pick)
    return keys.map(best)


def normalize_content_type(value):
    if not isinstance(value, str) or not value.strip():
        return "Unknown"
    k = value.strip().casefold()
    if k in ("course", "courses"):
        return "Course"
    if k in ("video", "videos"):
        return "Video"
    if k in ("article", "articles"):
        return "Article"
    if k in ("learning path", "learning paths", "learningpath", "path", "paths"):
        return "Learning Path"
    if k in ("document", "documents", "doc"):
        return "Document"
    return value.strip().title()


def fmt_int(v):
    return "—" if is_missing(v) else f"{int(round(float(v))):,}"


def fmt_hours(v):
    return "—" if is_missing(v) else f"{float(v):,.1f} h"


def fmt_pct(v):
    return "—" if is_missing(v) else f"{float(v):.0f}%"


def fmt_date(v, with_time=False):
    if is_missing(v):
        return "—"
    try:
        return pd.Timestamp(v).strftime("%d %b %Y %H:%M" if with_time else "%d %b %Y")
    except (TypeError, ValueError):
        return "—"


def pct(part, whole):
    return (part / whole * 100) if whole else float("nan")


def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def slug(value):
    return re.sub(r"\W+", "_", str(value)).strip("_")[:60] or "x"


def find_logo():
    names = ["AL-Bawani-logo.png", "al-bawani-logo.png", "AL-Bawani-Logo.png"]
    bases = [Path.cwd(), Path.cwd() / "assets"]
    try:
        here = Path(__file__).resolve().parent
        bases += [here, here / "assets"]
    except NameError:
        pass
    for base in bases:
        for name in names:
            candidate = base / name
            if candidate.exists():
                return candidate
    return None


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def section(title):
    st.markdown(f'<div class="section-title">{esc(title)}</div>', unsafe_allow_html=True)


def kpi(col, label, value, sub=None, accent=GREEN):
    sub_html = f'<div class="kpi-sub">{esc(sub)}</div>' if sub else ""
    col.markdown(
        f'<div class="kpi-card" style="border-left-color:{accent}">'
        f'<div class="kpi-label">{esc(label)}</div>'
        f'<div class="kpi-value">{esc(value)}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def badge(text):
    style = CELL_STYLES.get(str(text), _GREY_CELL)
    return f'<span class="badge" style="{style}">{esc(text)}</span>'


def show_table(df, status_cols=(), pct_cols=(), hour_cols=(), int_cols=(), date_cols=(),
               datetime_cols=(), height=None):
    """Professional table: status colouring, '—' for missing values, consistent number formats."""
    view = df.reset_index(drop=True)
    kwargs = {"use_container_width": True, "hide_index": True}
    if height:
        kwargs["height"] = height
    if view.empty:
        st.dataframe(view, **kwargs)
        return
    try:
        if view.size > 250000:
            raise ValueError("Table too large for styling")
        styler = view.style.format(na_rep="—")
        formats = {}
        for c in pct_cols:
            if c in view.columns:
                formats[c] = lambda v: "—" if is_missing(v) else f"{float(v):.0f}%"
        for c in hour_cols:
            if c in view.columns:
                formats[c] = lambda v: "—" if is_missing(v) else f"{float(v):,.2f}"
        for c in int_cols:
            if c in view.columns:
                formats[c] = lambda v: "—" if is_missing(v) else f"{int(round(float(v))):,}"
        for c in date_cols:
            if c in view.columns:
                formats[c] = lambda v: fmt_date(v)
        for c in datetime_cols:
            if c in view.columns:
                formats[c] = lambda v: fmt_date(v, with_time=True)
        if formats:
            styler = styler.format(formats, na_rep="—")
        cols = [c for c in status_cols if c in view.columns]
        if cols:
            mapper = getattr(styler, "map", None) or getattr(styler, "applymap")
            styler = mapper(lambda v: CELL_STYLES.get(str(v), ""), subset=cols)
        st.dataframe(styler, **kwargs)
    except Exception:
        st.dataframe(view, **kwargs)


def style_fig(fig, title, height=360):
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=15, color="#17452F")),
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Segoe UI, sans-serif", color=INK, size=12),
        margin=dict(l=10, r=10, t=80, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
    )
    fig.update_xaxes(gridcolor="#EEF2EF", zerolinecolor="#E3EBE5")
    fig.update_yaxes(gridcolor="#EEF2EF", zerolinecolor="#E3EBE5")
    return fig


def plot(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def dept_stacked_bar(df, status_col, order, colors, title):
    counts = df.groupby(["Department", status_col]).size().reset_index(name="Employees")
    if counts.empty:
        st.info("No data available for this chart.")
        return
    n = counts["Department"].nunique()
    fig = px.bar(
        counts, y="Department", x="Employees", color=status_col, orientation="h",
        color_discrete_map=colors, category_orders={status_col: order},
    )
    fig.update_layout(barmode="stack", xaxis_title="Employees", yaxis_title="")
    fig.update_yaxes(categoryorder="total ascending")
    plot(style_fig(fig, title, height=max(280, 36 * n + 130)))


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=64)
def parse_csv_bytes(raw):
    """Returns (DataFrame or None, error message or None). All values are read as text."""
    if raw is None:
        return None, None
    if not raw.strip():
        return pd.DataFrame(), None
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        encodings = ["utf-16"]
    else:
        encodings = ["utf-8-sig", "cp1252", "latin1"]
    text = None
    for enc in encodings:
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if text is None:
        return None, "The file encoding could not be read."
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return pd.DataFrame(), None
    first = lines[0]
    sep = max([",", ";", "\t"], key=first.count)
    try:
        df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False,
                         skip_blank_lines=True, on_bad_lines="skip")
    except pd.errors.EmptyDataError:
        return pd.DataFrame(), None
    except Exception as exc:  # noqa: BLE001 - report any parser problem to the user
        return None, f"The file could not be read as CSV ({exc})."
    df.columns = [str(c).strip().lstrip("﻿") for c in df.columns]
    keep = []
    for c in df.columns:
        empty_unnamed = str(c).startswith("Unnamed:") and (df[c].astype(str).str.strip() == "").all()
        keep.append(not empty_unnamed)
    df = df.loc[:, keep]
    if not df.empty and len(df.columns):
        blank = df.apply(lambda col: col.astype(str).str.strip() == "").all(axis=1)
        df = df.loc[~blank].reset_index(drop=True)
    return df, None


# ---------------------------------------------------------------------------
# Report preparation
# ---------------------------------------------------------------------------
def identity_columns(df):
    return {
        "name": find_col(df, NAME_CANDS),
        "first": find_col(df, ["First Name", "Given Name"]),
        "last": find_col(df, ["Last Name", "Surname", "Family Name"]),
        "email": find_col(df, EMAIL_CANDS),
        "uid": find_col(df, UID_CANDS),
        "dept": find_col(df, DEPT_CANDS),
        "title": find_col(df, TITLE_CANDS),
    }


def collect_uid_map(frames):
    """Unique User ID -> email, so reports that only carry one identifier still match."""
    mapping = {}
    for df in frames:
        if df is None or df.empty:
            continue
        cols = identity_columns(df)
        if not cols["email"] or not cols["uid"]:
            continue
        emails = to_object(clean_text(df[cols["email"]]).str.lower())
        uids = to_object(clean_text(df[cols["uid"]]))
        for uid, email in zip(uids.tolist(), emails.tolist()):
            if uid and email:
                mapping.setdefault(str(uid), str(email))
    return mapping


def identity_frame(df, cols, uid_map):
    idx = df.index
    email = text_or_na(df, cols["email"]).str.lower()
    uid = text_or_na(df, cols["uid"])
    if cols["name"]:
        name = text_or_na(df, cols["name"])
    elif cols["first"] or cols["last"]:
        name = (text_or_na(df, cols["first"]).fillna("") + " " + text_or_na(df, cols["last"]).fillna("")).str.strip()
        name = name.mask(name == "")
    else:
        name = na_text(idx)
    email_o = to_object(email)
    uid_o = to_object(uid)
    key = email_o.copy()
    mapped = uid_o.map(lambda v: uid_map.get(str(v)) if v is not None else None)
    key = key.where(key.notna(), mapped)
    uid_key = uid_o.map(lambda v: f"uid:{v}" if v is not None else None)
    key = key.where(key.notna(), uid_key)
    return pd.DataFrame({
        "Emp Key": key,
        "Employee Name": to_object(name),
        "Email": email_o,
        "Unique User ID": uid_o,
        "Department": to_object(text_or_na(df, cols["dept"])),
        "Business Title": to_object(text_or_na(df, cols["title"])),
    }, index=idx)


def missing_column_note(labels):
    return ("warn", "Columns not found: " + ", ".join(labels) + ".") if labels else None


@st.cache_data(show_spinner=False)
def prepare_management(raw, uid_map):
    notes = []
    meta = {"loaded": raw is not None, "has_login": False, "rows": 0}
    if raw is None:
        return None, notes, meta
    if raw.empty:
        notes.append(("warn", "The report is empty."))
        return pd.DataFrame(), notes, meta
    cols = identity_columns(raw)
    if not cols["email"] and not cols["uid"]:
        notes.append(("error", "No Email or Unique User ID column was found, so employees cannot be matched. "
                               "Check that this is the LearnerManagement export."))
        return pd.DataFrame(), notes, meta

    spec = {
        "License Assigned": (["License Assigned", "License Assigned Date"], ["licenseassigned"]),
        "License Status": (["License Status"], ["licensestatus"]),
        "Connected Profile Status": (["Connected Profile Status", "Profile Status"], ["connectedprofile"]),
        "Invitation Date": (["Invitation Date", "Invited Date", "Invite Date"], ["invitationdate", "invitedate"]),
        "Activation Date": (["Activation Date", "Activated Date"], ["activationdate", "activateddate"]),
        "Last Login": (["Last Login During Selected Time Range (PST/PDT)", "Last Login During Selected Time Range",
                        "Last Login", "Last Login Date"], ["lastlogin"]),
        "Days Logged In": (["Days Logged In"], ["dayslogged"]),
        "Hours Viewed": (["Hours Viewed"], ["hoursviewed"]),
    }
    found = {k: find_col(raw, c, p) for k, (c, p) in spec.items()}
    missing = [label for label, ok in [
        ("Name", cols["name"] or cols["first"] or cols["last"]), ("Email", cols["email"]),
        ("Business Title", cols["title"]), ("Unique User ID", cols["uid"]), ("Department", cols["dept"]),
    ] if not ok] + [k for k, v in found.items() if not v]
    note = missing_column_note(missing)
    if note:
        notes.append(note)

    df = identity_frame(raw, cols, uid_map)
    for field in ["License Assigned", "License Status", "Connected Profile Status"]:
        df[field] = to_object(text_or_na(raw, found[field]))
    for field in ["Invitation Date", "Activation Date", "Last Login"]:
        if found[field]:
            df[field], invalid = parse_dates(raw[found[field]])
            if invalid:
                notes.append(("warn", f"{invalid:,} invalid '{field}' values were treated as missing."))
        else:
            df[field] = na_dates(raw.index)
    df["Days Logged In"] = parse_number(raw[found["Days Logged In"]]) if found["Days Logged In"] else na_float(raw.index)
    df["Learning Hours"] = parse_hours(raw[found["Hours Viewed"]]) if found["Hours Viewed"] else na_float(raw.index)
    meta["has_login"] = bool(found["Last Login"] or found["Days Logged In"])
    if not meta["has_login"]:
        notes.append(("warn", "No login columns (Last Login / Days Logged In) were found. "
                              "Login status will show as 'Login Data Not Available'."))

    no_key = df["Emp Key"].isna()
    if no_key.any():
        notes.append(("warn", f"{int(no_key.sum()):,} rows without Email or Unique User ID were excluded."))
        df = df.loc[~no_key]
    n_dup = int(df["Emp Key"].duplicated().sum())
    if n_dup:
        notes.append(("info", f"{n_dup:,} duplicate employee rows were merged (row with the latest login kept)."))
        df = df.sort_values(["Last Login", "Days Logged In"], na_position="first").drop_duplicates("Emp Key", keep="last")
    no_email = int(df["Email"].isna().sum())
    if no_email:
        notes.append(("info", f"{no_email:,} employees have no email and are matched by Unique User ID."))
    meta["rows"] = len(df)
    notes.insert(0, ("ok", f"{len(df):,} employees loaded."))
    return df.reset_index(drop=True), notes, meta


@st.cache_data(show_spinner=False)
def prepare_summary(raw, uid_map):
    notes = []
    meta = {"loaded": raw is not None, "has_days": False, "has_views": False, "has_completions": False,
            "has_last": False, "rows": 0}
    if raw is None:
        return None, notes, meta
    if raw.empty:
        notes.append(("warn", "The report is empty."))
        return pd.DataFrame(), notes, meta
    cols = identity_columns(raw)
    if not cols["email"] and not cols["uid"]:
        notes.append(("error", "No Email or Unique User ID column was found, so employees cannot be matched."))
        return pd.DataFrame(), notes, meta
    spec = {
        "Days Logged In": (["Days Logged In"], ["dayslogged"]),
        "Hours Viewed": (["Hours Viewed"], ["hoursviewed"]),
        "Course Views": (["Course Views", "Courses Viewed"], ["courseview", "coursesviewed"]),
        "Course Completions": (["Course Completions", "Courses Completed"], ["coursecompletion", "coursescompleted"]),
        "Last Login": (["Last Login During Selected Time Range (PST/PDT)", "Last Login"], ["lastlogin"]),
    }
    found = {k: find_col(raw, c, p) for k, (c, p) in spec.items()}
    note = missing_column_note([k for k in ["Days Logged In", "Hours Viewed", "Course Views", "Course Completions"]
                                if not found[k]])
    if note:
        notes.append(note)
    df = identity_frame(raw, cols, uid_map)
    df["S Days"] = parse_number(raw[found["Days Logged In"]]) if found["Days Logged In"] else na_float(raw.index)
    df["S Hours"] = parse_hours(raw[found["Hours Viewed"]]) if found["Hours Viewed"] else na_float(raw.index)
    df["S Course Views"] = parse_number(raw[found["Course Views"]]) if found["Course Views"] else na_float(raw.index)
    df["S Course Completions"] = (parse_number(raw[found["Course Completions"]]) if found["Course Completions"]
                                  else na_float(raw.index))
    if found["Last Login"]:
        df["S Last Login"], invalid = parse_dates(raw[found["Last Login"]])
        if invalid:
            notes.append(("warn", f"{invalid:,} invalid 'Last Login' values were treated as missing."))
    else:
        df["S Last Login"] = na_dates(raw.index)
    meta.update(has_days=bool(found["Days Logged In"]), has_views=bool(found["Course Views"]),
                has_completions=bool(found["Course Completions"]), has_last=bool(found["Last Login"]))
    no_key = df["Emp Key"].isna()
    if no_key.any():
        notes.append(("warn", f"{int(no_key.sum()):,} rows without Email or Unique User ID were excluded."))
        df = df.loc[~no_key]
    n_dup = int(df["Emp Key"].duplicated().sum())
    if n_dup:
        notes.append(("info", f"{n_dup:,} duplicate employee rows were merged (highest activity kept)."))
        df = df.sort_values(["S Hours", "S Days"], na_position="first").drop_duplicates("Emp Key", keep="last")
    meta["rows"] = len(df)
    notes.insert(0, ("ok", f"{len(df):,} employees loaded."))
    return df.reset_index(drop=True), notes, meta


@st.cache_data(show_spinner=False)
def prepare_detail(raw, uid_map):
    notes = []
    meta = {"loaded": raw is not None, "ok": False, "has_type": False, "has_ids": False, "rows": 0}
    if raw is None:
        return None, notes, meta
    if raw.empty:
        notes.append(("warn", "The report is empty — no course activity is recorded for this period."))
        meta["ok"] = True
        return pd.DataFrame(), notes, meta
    cols = identity_columns(raw)
    if not cols["email"] and not cols["uid"]:
        notes.append(("error", "No Email or Unique User ID column was found, so employees cannot be matched."))
        return pd.DataFrame(), notes, meta
    spec = {
        "Content Name": (["Content Name", "Course Name", "Content Title", "Course Title", "Content"],
                         ["contentname", "coursename", "contenttitle", "coursetitle"]),
        "Content Type": (["Content Type", "Type", "Asset Type"], ["contenttype"]),
        "Content ID": (["Content ID", "Course ID", "Content Id", "Content URN", "Course URN", "Asset ID"],
                       ["contentid", "courseid", "contenturn"]),
        "Percent Completed": (["Percent Completed", "Percent Complete", "Completion Percentage", "% Completed",
                               "Progress"], ["percentcomplet", "completionpercent"]),
        "Completion Status": (["Completion Status", "Course Status", "Status", "Completed"], []),
        "Hours Viewed": (["Hours Viewed (LinkedIn Learning and Organization Content Only)", "Hours Viewed"],
                         ["hoursviewed"]),
        "Started": (["Started (PST/PDT)", "Started", "Start Date", "Started At"], ["startedat", "startdate", "started"]),
        "Last Viewed": (["Last Viewed During Time Range (PST/PDT)", "Last Viewed", "Last Viewed Date"], ["lastviewed"]),
        "Completed At": (["Completed At (PST/PDT)", "Completed At", "Completion Date", "Completed Date",
                          "Date Completed"], ["completedat", "completiondate", "completeddate", "datecompleted"]),
    }
    found = {k: find_col(raw, c, p) for k, (c, p) in spec.items()}
    if not found["Content Name"]:
        notes.append(("error", "No Content Name column was found, so course activity cannot be read."))
        return pd.DataFrame(), notes, meta
    note = missing_column_note([k for k in ["Content Type", "Content ID", "Percent Completed", "Hours Viewed",
                                            "Started", "Last Viewed", "Completed At"] if not found[k]])
    if note:
        notes.append(note)

    df = identity_frame(raw, cols, uid_map)
    df["Course Name"] = to_object(text_or_na(raw, found["Content Name"]))
    if found["Content Type"]:
        df["Content Type"] = to_object(text_or_na(raw, found["Content Type"])).map(normalize_content_type)
        meta["has_type"] = True
    else:
        df["Content Type"] = "Course"
        notes.append(("warn", "No Content Type column was found — every row is treated as a course, so "
                              "videos, articles or paths cannot be separated."))
    df["Is Course"] = df["Content Type"].eq("Course")
    df["Course ID"] = to_object(text_or_na(raw, found["Content ID"]))
    meta["has_ids"] = bool(df["Course ID"].notna().any())
    df["Progress"] = (parse_number(raw[found["Percent Completed"]]).clip(0, 100) if found["Percent Completed"]
                      else na_float(raw.index))
    df["Learning Hours"] = parse_hours(raw[found["Hours Viewed"]]) if found["Hours Viewed"] else na_float(raw.index)
    for label, field in [("Started Date", "Started"), ("Last Viewed", "Last Viewed"), ("Completed Date", "Completed At")]:
        if found[field]:
            df[label], invalid = parse_dates(raw[found[field]])
            if invalid:
                notes.append(("warn", f"{invalid:,} invalid '{field}' values were treated as missing."))
        else:
            df[label] = na_dates(raw.index)

    # Completion status — missing progress is never treated as zero.
    progress = df["Progress"]
    status_text = to_object(text_or_na(raw, found["Completion Status"]).str.casefold()).fillna("")
    status = pd.Series(UNKNOWN, index=df.index, dtype=object)
    status[progress.eq(0).to_numpy()] = NOT_STARTED
    status[progress.gt(0).to_numpy()] = IN_PROGRESS
    status[progress.ge(100).to_numpy()] = COMPLETED
    no_progress = progress.isna()
    status[(no_progress & status_text.isin(["not started"])).to_numpy()] = NOT_STARTED
    status[(no_progress & status_text.isin(["in progress", "in-progress", "started"])).to_numpy()] = IN_PROGRESS
    done = status_text.isin(["completed", "complete", "yes", "true", "done"]) | df["Completed Date"].notna()
    status[done.to_numpy()] = COMPLETED
    df["Status"] = status
    df["Status Rank"] = df["Status"].map(STATUS_RANK).astype(int)
    df["Course Name Norm"] = df["Course Name"].map(norm_title)
    cid = df["Course ID"]
    df["Course Key"] = [
        f"id:{str(i).casefold()}" if i is not None else f"name:{n}"
        for i, n in zip(cid.tolist(), df["Course Name Norm"].tolist())
    ]
    df["Activity Evidence"] = (
        progress.gt(0) | df["Learning Hours"].gt(0) | df["Last Viewed"].notna()
        | df["Status"].isin([COMPLETED, IN_PROGRESS])
    )

    no_key = df["Emp Key"].isna()
    if no_key.any():
        notes.append(("warn", f"{int(no_key.sum()):,} rows without Email or Unique User ID were excluded."))
        df = df.loc[~no_key]
    no_name = df["Course Name"].isna()
    if no_name.any():
        notes.append(("warn", f"{int(no_name.sum()):,} rows without a content name were excluded."))
        df = df.loc[~no_name]
    n_dup = int(df.duplicated(["Emp Key", "Course Key"]).sum())
    if n_dup:
        notes.append(("info", f"{n_dup:,} duplicate content records were merged (most advanced record kept)."))
        df = (df.sort_values(["Status Rank", "Progress", "Last Viewed"], ascending=False, na_position="last")
                .drop_duplicates(["Emp Key", "Course Key"], keep="first"))
    type_counts = df["Content Type"].value_counts()
    if len(type_counts):
        notes.append(("info", "Content types: " + ", ".join(f"{t} ({n:,})" for t, n in type_counts.items()) + "."))
    meta.update(ok=True, rows=len(df))
    notes.insert(0, ("ok", f"{len(df):,} content records loaded for {df['Emp Key'].nunique():,} employees."))
    return df.reset_index(drop=True), notes, meta


def build_master(mgmt, mgmt_meta, summ, summ_meta, det, det_meta):
    """One row per employee. LearnerManagement is the population; employees found only in
    other reports are added with login status 'Login Data Not Available'."""
    id_cols = ["Emp Key", "Employee Name", "Email", "Unique User ID", "Department", "Business Title"]
    pieces = []
    if summ is not None and not summ.empty:
        pieces.append(summ[id_cols])
    if det is not None and not det.empty:
        pieces.append(det[id_cols])
    if pieces:
        other = pd.concat(pieces, ignore_index=True).groupby("Emp Key", sort=False).first()
    else:
        other = pd.DataFrame(columns=id_cols[1:])

    has_mgmt = mgmt is not None and not mgmt.empty
    if has_mgmt:
        master = mgmt.copy()
        master["In Learner Management"] = True
        known = set(master["Emp Key"])
        extra_keys = [k for k in other.index if k not in known]
    else:
        master = None
        extra_keys = list(other.index)
    if extra_keys:
        extra = other.loc[extra_keys].reset_index().rename(columns={"index": "Emp Key"})
        extra["In Learner Management"] = False
        master = extra if master is None else pd.concat([master, extra], ignore_index=True)
    if master is None:
        return pd.DataFrame()
    master = master.reset_index(drop=True)

    for c in ["License Assigned", "License Status", "Connected Profile Status"]:
        if c not in master.columns:
            master[c] = None
    for c in ["Invitation Date", "Activation Date", "Last Login"]:
        master[c] = pd.to_datetime(master[c], errors="coerce") if c in master.columns else pd.NaT
    for c in ["Days Logged In", "Learning Hours"]:
        master[c] = to_float(master[c]) if c in master.columns else float("nan")
    master["In Learner Management"] = master["In Learner Management"].fillna(False).astype(bool)

    if not other.empty:
        for c in id_cols[1:]:
            fill = master["Emp Key"].map(other[c])
            master[c] = master[c].astype(object).where(master[c].notna(), fill)
    name = master["Employee Name"].astype(object)
    name = name.where(name.notna(), master["Email"]).where(lambda s: s.notna(), master["Unique User ID"])
    master["Employee Name"] = name.where(name.notna(), "Unknown Employee")

    s_cols = ["S Days", "S Hours", "S Course Views", "S Course Completions", "S Last Login"]
    if summ is not None and not summ.empty:
        master = master.merge(summ[["Emp Key"] + s_cols], on="Emp Key", how="left")
        master["In Learner Summary"] = master["Emp Key"].isin(set(summ["Emp Key"]))
    else:
        for c in s_cols:
            master[c] = pd.NaT if c == "S Last Login" else float("nan")
        master["In Learner Summary"] = False
    master["S Last Login"] = pd.to_datetime(master["S Last Login"], errors="coerce")
    for c in ["S Days", "S Hours", "S Course Views", "S Course Completions"]:
        master[c] = to_float(master[c])

    # ---- Login status (separate from course activity) ----
    mg_days = master["Days Logged In"]
    mg_last = master["Last Login"]
    s_days = master["S Days"]
    s_last = master["S Last Login"]
    in_mgmt = master["In Learner Management"]
    in_summ = master["In Learner Summary"].astype(bool)
    s_logged = in_summ & (s_last.notna() | s_days.gt(0))
    s_known = in_summ & (s_last.notna() | s_days.notna())

    status = pd.Series(LOGIN_NA, index=master.index, dtype=object)
    source = pd.Series("—", index=master.index, dtype=object)
    if mgmt_meta.get("has_login"):
        logged = mg_last.notna() | mg_days.gt(0)
        status[(in_mgmt & logged).to_numpy()] = LOGGED_IN
        status[(in_mgmt & ~logged).to_numpy()] = NO_LOGIN
        # Evidence of a login in LearnerSummary overrides an empty LearnerManagement cell.
        status[(in_mgmt & ~logged & s_logged).to_numpy()] = LOGGED_IN
        source[in_mgmt.to_numpy()] = "LearnerManagement"
    if summ_meta.get("has_days") or summ_meta.get("has_last"):
        cand = status.eq(LOGIN_NA) & s_known
        status[(cand & s_logged).to_numpy()] = LOGGED_IN
        status[(cand & ~s_logged).to_numpy()] = NO_LOGIN
        source[cand.to_numpy()] = "LearnerSummary"
    master["Login Status"] = status
    master["Login Source"] = source
    master["Last Login"] = mg_last.where(mg_last.notna(), s_last)
    master["Days Logged In"] = mg_days.where(mg_days.notna(), s_days)

    # ---- Learning hours: LearnerManagement -> LearnerSummary -> LearnerDetail ----
    hours = master["Learning Hours"].where(master["Learning Hours"].notna(), master["S Hours"])
    det_ok = bool(det_meta.get("ok"))
    if det_ok and det is not None and not det.empty:
        det_hours = det.groupby("Emp Key")["Learning Hours"].sum(min_count=1)
        hours = hours.where(hours.notna(), master["Emp Key"].map(det_hours))
    master["Learning Hours"] = to_float(hours)

    # ---- Course activity ----
    if det_ok:
        if det is not None and not det.empty:
            courses = det[det["Is Course"]]
            active = set(courses.loc[courses["Activity Evidence"], "Emp Key"])
            completed = courses[courses["Status"] == COMPLETED].groupby("Emp Key")["Course Key"].nunique()
            records = courses.groupby("Emp Key")["Course Key"].nunique()
        else:
            active, completed, records = set(), pd.Series(dtype=float), pd.Series(dtype=float)
        master["Course Activity Status"] = master["Emp Key"].isin(active).map({True: ACT_YES, False: ACT_NO})
        # LearnerDetail is loaded, so an employee absent from it has 0 recorded completions in the period.
        master["Courses Completed"] = to_float(master["Emp Key"].map(completed)).fillna(0)
        master["Course Records"] = to_float(master["Emp Key"].map(records)).fillna(0)
    elif summ_meta.get("has_views"):
        views = master["S Course Views"]
        act = pd.Series(ACT_NA, index=master.index, dtype=object)
        act[(in_summ & views.gt(0)).to_numpy()] = ACT_YES
        act[(in_summ & views.eq(0)).to_numpy()] = ACT_NO
        master["Course Activity Status"] = act
        master["Courses Completed"] = master["S Course Completions"]
        master["Course Records"] = float("nan")
    else:
        master["Course Activity Status"] = ACT_NA
        master["Courses Completed"] = master["S Course Completions"]
        master["Course Records"] = float("nan")

    master["Department"] = canonical_departments(master["Department"])
    return master


# ---------------------------------------------------------------------------
# Mandatory course configuration & evaluation
# ---------------------------------------------------------------------------
def empty_slots():
    return [{"name": "", "course_id": ""} for _ in range(3)]


def normalize_slots(value):
    slots = []
    if isinstance(value, dict):
        value = value.get("courses", [])
    if isinstance(value, list):
        for item in value[:3]:
            if isinstance(item, str):
                slots.append({"name": item.strip(), "course_id": ""})
            elif isinstance(item, dict):
                slots.append({
                    "name": str(item.get("name") or item.get("course_name") or "").strip(),
                    "course_id": str(item.get("course_id") or item.get("id") or "").strip(),
                })
            else:
                slots.append({"name": "", "course_id": ""})
    while len(slots) < 3:
        slots.append({"name": "", "course_id": ""})
    return slots


def parse_config_json(raw):
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "The configuration file is not valid JSON."
    if isinstance(data, dict) and isinstance(data.get("departments"), dict):
        data = data["departments"]
    if not isinstance(data, dict):
        return None, "The configuration file does not contain department courses."
    config = {str(k).strip(): normalize_slots(v) for k, v in data.items() if str(k).strip()}
    return config, None


def slot_filled(slot):
    return bool((slot.get("name") or "").strip() or (slot.get("course_id") or "").strip())


def is_configured(slots):
    return bool(slots) and len(slots) == 3 and all(slot_filled(s) for s in slots)


def slot_label(slot):
    name = (slot.get("name") or "").strip()
    cid = (slot.get("course_id") or "").strip()
    if name and cid:
        return f"{name} (ID {cid})"
    return name or (f"Course ID {cid}" if cid else "—")


def config_lookup(config):
    return {dept_key(k): v for k, v in config.items()}


def match_slot(ec, slot, use_ids, det_ok, hist):
    """Course ID match when both sides have an ID; otherwise a normalised exact-name match.
    Similar titles are never treated as the same course."""
    cid = (slot.get("course_id") or "").strip()
    nname = norm_title(slot.get("name"))
    result = {
        "Matched Course": None,
        "Completion Status": NOT_STARTED if det_ok else UNKNOWN,
        "Progress": float("nan"),
        "Matched By": "—",
        "Source": "No record in LearnerDetail" if det_ok else "LearnerDetail not available",
    }
    by_id = bool(cid and use_ids)
    if ec is not None and not ec.empty:
        if by_id:
            m = ec[ec["Course ID"].fillna("").astype(str).str.casefold() == cid.casefold()]
        elif nname:
            m = ec[ec["Course Name Norm"] == nname]
        else:
            m = ec.iloc[0:0]
        if not m.empty:
            best = m.sort_values(["Status Rank", "Progress"], ascending=False, na_position="last").iloc[0]
            result.update({
                "Matched Course": best["Course Name"],
                "Completion Status": best["Status"],
                "Progress": best["Progress"],
                "Matched By": "Course ID" if by_id else "Course name",
                "Source": "Current report",
            })
    if result["Completion Status"] != COMPLETED and hist is not None and not hist.empty:
        if cid and hist["Course ID"].notna().any():
            hm = hist[hist["Course ID"].fillna("").astype(str).str.casefold() == cid.casefold()]
            how = "Course ID"
        elif nname:
            hm = hist[hist["Course Name Norm"] == nname]
            how = "Course name"
        else:
            hm = hist.iloc[0:0]
            how = "—"
        if not hm.empty:
            result.update({
                "Matched Course": hm.iloc[-1]["Course Name"],
                "Completion Status": COMPLETED,
                "Progress": 100.0,
                "Matched By": how,
                "Source": f"Earlier period: {hm.iloc[-1]['Period']}",
            })
    return result


EMP_MAND_COLS = ["Emp Key", "Department", "Mandatory Completed", "Mandatory Remaining", "Mandatory %",
                 "All Mandatory Completed"]
LONG_MAND_COLS = ["Emp Key", "Employee Name", "Email", "Department", "Slot", "Required Course", "Matched Course",
                  "Completion Status", "Progress", "Matched By", "Source"]


def evaluate_mandatory(master, det, det_ok, config, history_done):
    lookup = config_lookup(config)
    courses = det[det["Is Course"]] if (det_ok and det is not None and not det.empty) else None
    use_ids = bool(courses is not None and courses["Course ID"].notna().any())
    by_emp = {k: g for k, g in courses.groupby("Emp Key", sort=False)} if courses is not None else {}
    hist_by_emp = ({k: g for k, g in history_done.groupby("Email Key", sort=False)}
                   if history_done is not None and not history_done.empty else {})
    emp_rows, long_rows = [], []
    subset = master[["Emp Key", "Employee Name", "Email", "Department"]]
    for key, name, email, dept in subset.itertuples(index=False, name=None):
        slots = lookup.get(dept_key(dept))
        if not is_configured(slots):
            continue
        ec = by_emp.get(key)
        hist = hist_by_emp.get(key)
        done = 0
        for i, slot in enumerate(slots, 1):
            res = match_slot(ec, slot, use_ids, det_ok, hist)
            done += int(res["Completion Status"] == COMPLETED)
            long_rows.append({"Emp Key": key, "Employee Name": name, "Email": email, "Department": dept,
                              "Slot": i, "Required Course": slot_label(slot), **res})
        emp_rows.append({"Emp Key": key, "Department": dept, "Mandatory Completed": done,
                         "Mandatory Remaining": 3 - done, "Mandatory %": done / 3 * 100,
                         "All Mandatory Completed": done == 3})
    return pd.DataFrame(emp_rows, columns=EMP_MAND_COLS), pd.DataFrame(long_rows, columns=LONG_MAND_COLS)


def course_catalog(det, content_raw):
    """Courses available in the uploaded reports, for the manual mapping selector."""
    frames = []
    if det is not None and not det.empty:
        frames.append(det.loc[det["Is Course"], ["Course Name", "Course ID"]])
    if content_raw is not None and not content_raw.empty:
        n = find_col(content_raw, ["Content Name", "Course Name", "Content Title", "Course Title"], ["contentname"])
        if n:
            t = find_col(content_raw, ["Content Type", "Type"], ["contenttype"])
            i = find_col(content_raw, ["Content ID", "Course ID", "Content URN"], ["contentid", "courseid"])
            cdf = pd.DataFrame({"Course Name": to_object(text_or_na(content_raw, n)),
                                "Course ID": to_object(text_or_na(content_raw, i))})
            if t:
                types = to_object(text_or_na(content_raw, t)).map(normalize_content_type)
                cdf = cdf[(types == "Course").to_numpy()]
            frames.append(cdf)
    if not frames:
        return {}
    cat = pd.concat(frames, ignore_index=True)
    cat = cat[cat["Course Name"].notna()].copy()
    cat["norm"] = cat["Course Name"].map(norm_title)
    cat = cat.drop_duplicates("norm", keep="first").sort_values("norm")
    catalog = {}
    for name, cid in zip(cat["Course Name"].tolist(), cat["Course ID"].tolist()):
        cid = "" if is_missing(cid) else str(cid)
        label = f"{name}  ·  ID {cid}" if cid else str(name)
        base, n = label, 2
        while label in catalog:
            label = f"{base} ({n})"
            n += 1
        catalog[label] = {"name": str(name), "course_id": cid}
    return catalog


def catalog_label_for(catalog, slot):
    cid = (slot.get("course_id") or "").strip().casefold()
    nname = norm_title(slot.get("name"))
    if not cid and not nname:
        return None
    for label, rec in catalog.items():
        if cid and rec["course_id"].casefold() == cid:
            return label
    if not cid:
        for label, rec in catalog.items():
            if norm_title(rec["name"]) == nname:
                return label
    return None


# ---------------------------------------------------------------------------
# Monthly history
# ---------------------------------------------------------------------------
def load_archive(raw):
    notes = []
    if raw is None:
        return None, notes
    if raw.empty:
        notes.append(("warn", "The history archive is empty."))
        return None, notes
    period_col = find_col(raw, ["Period"])
    key_col = find_col(raw, ["Email Key"])
    if not period_col or not key_col:
        notes.append(("error", "The archive must contain 'Period' and 'Email Key' columns (download it from this app)."))
        return None, notes
    df = raw.copy()
    rename = {}
    for col in HISTORY_COLUMNS:
        found = find_col(df, [col])
        if found and found != col:
            rename[found] = col
    df = df.rename(columns=rename)
    for col in HISTORY_COLUMNS:
        if col not in df.columns:
            df[col] = None
    for col in ["Record Type", "Period", "Period Start", "Period End", "Email Key", "Employee Name", "Department",
                "Login Status", "Course Activity Status", "Course Key", "Course ID", "Course Name", "Content Type",
                "Status", "Completed Date"]:
        df[col] = to_object(clean_text(df[col].astype(object).where(df[col].notna(), "")))
    df["Record Type"] = df["Record Type"].fillna("Course")
    for col in ["Progress", "Learning Hours", "Days Logged In", "Courses Completed"]:
        df[col] = parse_number(df[col].astype(object).where(df[col].notna(), ""))
    df = df[df["Period"].notna() & df["Email Key"].notna()]
    notes.append(("ok", f"{len(df):,} archived records across {df['Period'].nunique():,} periods loaded."))
    return df[HISTORY_COLUMNS].reset_index(drop=True), notes


def history_completions(archive, current_label):
    if archive is None or archive.empty:
        return None
    h = archive[(archive["Record Type"] == "Course") & (archive["Period"] != current_label)
                & (archive["Status"] == COMPLETED)].copy()
    if h.empty:
        return None
    h["Course Name Norm"] = h["Course Name"].map(norm_title)
    return h[["Email Key", "Period", "Course ID", "Course Name", "Course Name Norm"]]


def build_snapshot(master, det, det_ok, label, start, end):
    access = pd.DataFrame({
        "Record Type": "Employee Access",
        "Period": label,
        "Period Start": start.isoformat(),
        "Period End": end.isoformat(),
        "Email Key": master["Emp Key"],
        "Employee Name": master["Employee Name"],
        "Department": master["Department"],
        "Login Status": master["Login Status"],
        "Days Logged In": master["Days Logged In"],
        "Course Activity Status": master["Course Activity Status"],
        "Courses Completed": master["Courses Completed"],
        "Learning Hours": master["Learning Hours"],
    }).reindex(columns=HISTORY_COLUMNS)
    frames = [access]
    if det_ok and det is not None and not det.empty:
        c = det[det["Is Course"]]
        if not c.empty:
            names = master.set_index("Emp Key")["Employee Name"]
            course = pd.DataFrame({
                "Record Type": "Course",
                "Period": label,
                "Period Start": start.isoformat(),
                "Period End": end.isoformat(),
                "Email Key": c["Emp Key"],
                "Employee Name": c["Emp Key"].map(names),
                "Department": c["Department"],
                "Course Key": c["Course Key"],
                "Course ID": c["Course ID"],
                "Course Name": c["Course Name"],
                "Content Type": c["Content Type"],
                "Progress": c["Progress"],
                "Status": c["Status"],
                "Learning Hours": c["Learning Hours"],
                "Completed Date": c["Completed Date"].dt.strftime("%Y-%m-%d"),
            }).reindex(columns=HISTORY_COLUMNS)
            frames.append(course)
    return pd.concat(frames, ignore_index=True)


def ordered_periods(hist):
    order = hist.drop_duplicates("Period")[["Period", "Period Start"]].copy()
    order["_start"] = pd.to_datetime(order["Period Start"], errors="coerce")
    order["_pos"] = range(len(order))
    if len(order) and order["_start"].notna().all():
        order = order.sort_values(["_start", "_pos"])
    return order["Period"].tolist()


def period_metrics(hist):
    rows = []
    for p in ordered_periods(hist):
        a = hist[(hist["Record Type"] == "Employee Access") & (hist["Period"] == p)]
        c = hist[(hist["Record Type"] == "Course") & (hist["Period"] == p)]
        has_a = not a.empty
        rows.append({
            "Period": p,
            "Employees": a["Email Key"].nunique() if has_a else float("nan"),
            "Logged In": int((a["Login Status"] == LOGGED_IN).sum()) if has_a else float("nan"),
            "No Login During Selected Period": int((a["Login Status"] == NO_LOGIN).sum()) if has_a else float("nan"),
            "Course Learners": c["Email Key"].nunique(),
            "Course Completions": int((c["Status"] == COMPLETED).sum()),
            "Learning Hours": (a["Learning Hours"].sum(min_count=1) if has_a
                               else c["Learning Hours"].sum(min_count=1)),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "mandatory_config" not in st.session_state:
    st.session_state["mandatory_config"] = {}
if "cfg_version" not in st.session_state:
    st.session_state["cfg_version"] = 0

# ---------------------------------------------------------------------------
# Sidebar: navigation, period, uploads
# ---------------------------------------------------------------------------
logo_path = find_logo()
with st.sidebar:
    if logo_path:
        st.image(str(logo_path), width=170)
    st.markdown("## Learning Hub")
    st.caption("AL BAWANI | PEOPLE DEVELOPMENT")
    page = st.radio("Navigation", PAGES, key="nav_page")
    st.divider()

    st.markdown("### Reporting Period")
    period_value = st.date_input(
        "Selected reporting period",
        value=(DEFAULT_PERIOD_START, DEFAULT_PERIOD_END),
        format="DD/MM/YYYY",
        key="period_dates",
    )
    if isinstance(period_value, (list, tuple)) and len(period_value) == 2:
        period_start, period_end = period_value
    elif isinstance(period_value, (list, tuple)) and len(period_value) == 1:
        period_start = period_end = period_value[0]
    elif isinstance(period_value, date):
        period_start = period_end = period_value
    else:
        period_start, period_end = DEFAULT_PERIOD_START, DEFAULT_PERIOD_END
    default_label = f"{period_start:%d %b %Y} – {period_end:%d %b %Y}"
    period_label = st.text_input(
        "Period label (used in Monthly History)",
        value=default_label,
        key=f"period_label_{period_start}_{period_end}",
    ).strip() or default_label
    st.caption("Login status reflects this reporting period only.")
    st.divider()

    uploads = {}
    with st.expander("LinkedIn Learning Reports", expanded=True):
        for rkey, rlabel, rhelp in REPORT_SPECS:
            uploads[rkey] = st.file_uploader(rlabel, type=["csv"], key=f"upload_{rkey}", help=rhelp)

    with st.expander("Mandatory Course Configuration"):
        cfg_file = st.file_uploader("Import configuration (JSON)", type=["json"], key="cfg_upload")
        if cfg_file is not None:
            signature = (cfg_file.name, cfg_file.size)
            if st.session_state.get("cfg_applied") != signature:
                parsed, cfg_error = parse_config_json(cfg_file.getvalue())
                if cfg_error:
                    st.error(cfg_error)
                else:
                    st.session_state["mandatory_config"] = parsed
                    st.session_state["cfg_version"] += 1
                    st.session_state["cfg_applied"] = signature
                    st.session_state["cfg_import_msg"] = f"Configuration imported for {len(parsed)} departments."
            if st.session_state.get("cfg_import_msg"):
                st.success(st.session_state["cfg_import_msg"])
        st.caption("Configuration is kept for this browser session only. Export it from "
                   "Mandatory Program → Administrator Configuration and import it here next time.")

    with st.expander("Monthly History Archive"):
        archive_file = st.file_uploader("Previous history archive (CSV)", type=["csv"], key="archive_upload")
        st.caption("Upload the archive downloaded from Monthly History in a previous session.")

    report_status_box = st.container()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
head_left, head_right = st.columns([1, 6], vertical_alignment="center")
with head_left:
    if logo_path:
        st.image(str(logo_path), width=150)
    else:
        st.markdown(f"<div style='font-size:22px;font-weight:800;color:{GREEN}'>AL BAWANI</div>",
                    unsafe_allow_html=True)
with head_right:
    st.markdown(
        '<div class="ab-header"><div>'
        '<div class="ab-eyebrow">People Development</div>'
        '<div class="ab-title">Learning &amp; Development Dashboard</div>'
        '<div class="ab-subtitle">LinkedIn Learning access, course progress and mandatory learning</div>'
        f'</div><div class="ab-period">Reporting period: {esc(period_label)}</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Load & prepare data
# ---------------------------------------------------------------------------
raw = {}
validation = {}
for rkey, rlabel, _ in REPORT_SPECS:
    validation[rkey] = []
    upload = uploads.get(rkey)
    if upload is None:
        raw[rkey] = None
        continue
    frame, read_error = parse_csv_bytes(upload.getvalue())
    if read_error:
        validation[rkey].append(("error", read_error))
        raw[rkey] = None
    else:
        raw[rkey] = frame
        if frame is not None and frame.empty and rkey not in ("management", "summary", "detail"):
            validation[rkey].append(("warn", "The report is empty."))
        elif frame is not None and rkey not in ("management", "summary", "detail"):
            validation[rkey].append(("ok", f"{len(frame):,} rows loaded."))

uid_map = collect_uid_map([raw["management"], raw["summary"], raw["detail"]])
mgmt, mgmt_notes, mgmt_meta = prepare_management(raw["management"], uid_map)
summ, summ_notes, summ_meta = prepare_summary(raw["summary"], uid_map)
det, det_notes, det_meta = prepare_detail(raw["detail"], uid_map)
validation["management"] += mgmt_notes
validation["summary"] += summ_notes
validation["detail"] += det_notes
det_ok = bool(det_meta.get("ok"))

archive_raw, archive_error = (parse_csv_bytes(archive_file.getvalue()) if archive_file is not None else (None, None))
archive, archive_notes = load_archive(archive_raw)
if archive_error:
    archive_notes.append(("error", archive_error))

with report_status_box:
    st.markdown("### Report Status")
    icons = {"ok": "✅", "warn": "⚠️", "error": "⛔", "info": "ℹ️"}
    for rkey, rlabel, _ in REPORT_SPECS:
        notes = validation[rkey]
        if uploads.get(rkey) is None:
            st.caption(f"▫️ {rlabel} — not uploaded")
            continue
        levels = [lvl for lvl, _ in notes]
        icon = icons["error"] if "error" in levels else icons["warn"] if "warn" in levels else icons["ok"]
        st.caption(f"{icon} {rlabel}")

master = build_master(mgmt, mgmt_meta, summ, summ_meta, det, det_meta)
if master.empty:
    st.info("Upload **LearnerManagement**, **LearnerSummary** and **LearnerDetail** in the sidebar to begin. "
            "LearnerManagement provides login status; LearnerDetail provides course progress.")
    problems = [(label, lvl, msg) for key, label, _ in REPORT_SPECS for lvl, msg in validation[key]
                if lvl in ("error", "warn")]
    for label, lvl, msg in problems:
        (st.error if lvl == "error" else st.warning)(f"{label}: {msg}")
    st.markdown('<div class="ab-footer">AL BAWANI | LEARNING &amp; DEVELOPMENT</div>', unsafe_allow_html=True)
    st.stop()

if det is not None and not det.empty:
    det = det.copy()
    det["Department"] = det["Emp Key"].map(master.set_index("Emp Key")["Department"]).fillna(NO_DEPT)

has_mgmt = mgmt is not None and not mgmt.empty
departments = sorted(master["Department"].dropna().unique().tolist())

config = st.session_state["mandatory_config"]
history_done = history_completions(archive, period_label)
mand_emp, mand_long = evaluate_mandatory(master, det, det_ok, config, history_done)
lookup = config_lookup(config)
configured_depts = [d for d in departments if is_configured(lookup.get(dept_key(d)))]

# ---------------------------------------------------------------------------
# Global department filter
# ---------------------------------------------------------------------------
fcol, ccol = st.columns([2, 5], vertical_alignment="bottom")
with fcol:
    dept_filter = st.selectbox("Department", [ALL_DEPTS] + departments, key="dept_filter")
scope = master if dept_filter == ALL_DEPTS else master[master["Department"] == dept_filter]
scope_keys = set(scope["Emp Key"])
det_scope = det[det["Emp Key"].isin(scope_keys)] if (det is not None and not det.empty) else None
mand_emp_scope = mand_emp[mand_emp["Emp Key"].isin(scope_keys)]
mand_long_scope = mand_long[mand_long["Emp Key"].isin(scope_keys)]
with ccol:
    st.caption(f"Showing {len(scope):,} employees · {dept_filter}")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def render_notice():
    st.markdown(
        '<div class="notice">'
        '<div class="notice-title">Employee Access Status – Important Note</div>'
        '<div class="notice-lead">Login activity and course activity are tracked separately.</div>'
        '<div class="notice-grid">'
        '<div><b>No Login During Selected Period:</b> No login was recorded during the selected reporting period. '
        'This does not necessarily mean the employee has never accessed the platform.</div>'
        '<div><b>No Course Activity:</b> No course activity appears in the available learning report. '
        'The employee may still have logged in.</div>'
        '<div><b>Login Data Not Available:</b> Login information is not available to verify the employee\'s '
        'access status.</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def total_course_completions(frame_scope, det_frame):
    if det_ok:
        if det_frame is None or det_frame.empty:
            return 0
        return int(((det_frame["Status"] == COMPLETED) & det_frame["Is Course"]).sum())
    values = frame_scope["Courses Completed"]
    return values.sum(min_count=1)


def page_overview():
    render_notice()
    n = len(scope)
    login_counts = scope["Login Status"].value_counts()
    act_counts = scope["Course Activity Status"].value_counts()
    logged = int(login_counts.get(LOGGED_IN, 0))
    no_login = int(login_counts.get(NO_LOGIN, 0))
    login_na = int(login_counts.get(LOGIN_NA, 0))
    with_act = int(act_counts.get(ACT_YES, 0))
    no_act = int(act_counts.get(ACT_NO, 0))
    act_na = int(act_counts.get(ACT_NA, 0))
    licensed = int(scope["In Learner Management"].sum())
    hours = scope["Learning Hours"].sum(min_count=1)
    completions = total_course_completions(scope, det_scope)

    section("Employee Access")
    row = st.columns(4)
    kpi(row[0], "Total Licensed Employees", fmt_int(licensed) if has_mgmt else "—",
        None if has_mgmt else "LearnerManagement not uploaded")
    kpi(row[1], "Logged In", fmt_int(logged), f"{fmt_pct(pct(logged, n))} of employees")
    kpi(row[2], "No Login During Selected Period", fmt_int(no_login), f"{fmt_pct(pct(no_login, n))} of employees",
        accent=GOLD)
    kpi(row[3], "Login Data Not Available", fmt_int(login_na), f"{fmt_pct(pct(login_na, n))} of employees",
        accent=GREY)
    extra = n - licensed
    if has_mgmt and extra > 0:
        st.caption(f"{extra:,} employees appear in learning reports but not in LearnerManagement. They are "
                   "included; their login status comes from LearnerSummary where available, otherwise "
                   "'Login Data Not Available'.")

    section("Learning Activity")
    show_mand = bool(configured_depts) and not mand_emp_scope.empty
    row = st.columns(5 if show_mand else 4)
    act_sub = f"{act_na:,} without course data" if act_na else f"{fmt_pct(pct(with_act, n))} of employees"
    kpi(row[0], "Employees with Course Activity", fmt_int(with_act), act_sub)
    kpi(row[1], "Employees with No Course Activity", fmt_int(no_act), "May still have logged in", accent=GOLD)
    kpi(row[2], "Total Course Completions", fmt_int(completions), "Courses only (excludes videos, articles, paths)")
    kpi(row[3], "Total Learning Hours", fmt_hours(hours))
    if show_mand:
        done = int(mand_emp_scope["All Mandatory Completed"].sum())
        total = len(mand_emp_scope)
        kpi(row[4], "Mandatory Completion Rate", fmt_pct(pct(done, total)),
            f"{done:,} of {total:,} completed all 3", accent=GOLD)

    section("By Department")
    c1, c2 = st.columns(2)
    with c1:
        dept_stacked_bar(scope, "Login Status", LOGIN_ORDER, LOGIN_COLORS, "Login Status by Department")
    with c2:
        dept_stacked_bar(scope, "Course Activity Status", ACTIVITY_ORDER, ACTIVITY_COLORS,
                         "Course Activity by Department")
    if show_mand:
        md = (mand_emp_scope.groupby("Department")
              .agg(Employees=("Emp Key", "nunique"), Completed=("All Mandatory Completed", "sum"))
              .reset_index())
        md["Completion Rate"] = md["Completed"] / md["Employees"] * 100
        md = md.sort_values("Completion Rate")
        fig = px.bar(md, y="Department", x="Completion Rate", orientation="h",
                     text=md["Completion Rate"].map(lambda v: f"{v:.0f}%"),
                     color_discrete_sequence=[GREEN],
                     hover_data={"Employees": True, "Completed": True, "Completion Rate": ":.0f"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="Employees who completed all 3 mandatory courses (%)", yaxis_title="",
                          xaxis_range=[0, 110], showlegend=False)
        plot(style_fig(fig, "Mandatory Completion by Department", height=max(260, 36 * len(md) + 130)))
    elif not configured_depts:
        st.caption(f"Mandatory completion by department: {NOT_CONFIGURED}.")

    summary = (scope.groupby("Department")
               .agg(Employees=("Emp Key", "nunique"),
                    Logged_In=("Login Status", lambda s: int((s == LOGGED_IN).sum())),
                    With_Activity=("Course Activity Status", lambda s: int((s == ACT_YES).sum())),
                    Completions=("Courses Completed", lambda s: s.sum(min_count=1)),
                    Hours=("Learning Hours", lambda s: s.sum(min_count=1)))
               .reset_index())
    summary["Logged In %"] = summary["Logged_In"] / summary["Employees"] * 100
    summary["Course Activity %"] = summary["With_Activity"] / summary["Employees"] * 100
    if not mand_emp_scope.empty:
        rate = mand_emp_scope.groupby("Department")["All Mandatory Completed"].mean() * 100
        summary["Mandatory Completion"] = summary["Department"].map(rate)
    else:
        summary["Mandatory Completion"] = float("nan")
    summary = summary.rename(columns={"Logged_In": "Logged In", "With_Activity": "With Course Activity",
                                      "Completions": "Course Completions", "Hours": "Learning Hours"})
    summary = summary[["Department", "Employees", "Logged In", "Logged In %", "With Course Activity",
                       "Course Activity %", "Course Completions", "Learning Hours", "Mandatory Completion"]]
    section("Department Summary")
    show_table(summary, pct_cols=["Logged In %", "Course Activity %", "Mandatory Completion"],
               hour_cols=["Learning Hours"], int_cols=["Employees", "Logged In", "With Course Activity",
                                                       "Course Completions"])
    st.caption("Mandatory Completion shows '—' where the department's three mandatory courses are not configured.")

    with st.expander("Data quality checks"):
        for rkey, rlabel, _ in REPORT_SPECS:
            notes = validation[rkey]
            if uploads.get(rkey) is None:
                st.markdown(f"**{rlabel}** — not uploaded")
                continue
            st.markdown(f"**{rlabel}**")
            for lvl, msg in notes:
                st.markdown(f"- {msg}")
        if archive_notes:
            st.markdown("**Monthly History Archive**")
            for lvl, msg in archive_notes:
                st.markdown(f"- {msg}")


def page_access():
    section("Employee Access")
    c1, c2, c3 = st.columns([1.3, 1.3, 1.6])
    with c1:
        login_sel = st.multiselect("Login Status", LOGIN_ORDER, default=[], placeholder="All login statuses",
                                   key="acc_login")
    with c2:
        act_sel = st.multiselect("Course Activity Status", ACTIVITY_ORDER, default=[], placeholder="All",
                                 key="acc_act")
    with c3:
        search = st.text_input("Search", placeholder="Name, email or user ID", key="acc_search").strip()
    view = scope.copy()
    if login_sel:
        view = view[view["Login Status"].isin(login_sel)]
    if act_sel:
        view = view[view["Course Activity Status"].isin(act_sel)]
    if search:
        mask = pd.Series(False, index=view.index)
        for col in ["Employee Name", "Email", "Unique User ID"]:
            mask |= view[col].astype(str).str.contains(search, case=False, regex=False, na=False)
        view = view[mask]
    table = view[["Employee Name", "Department", "Business Title", "Email", "Login Status", "Last Login",
                  "Days Logged In", "Learning Hours", "Course Activity Status"]].sort_values("Employee Name")
    st.caption(f"{len(table):,} of {len(scope):,} employees")
    show_table(table, status_cols=["Login Status", "Course Activity Status"], datetime_cols=["Last Login"],
               int_cols=["Days Logged In"], hour_cols=["Learning Hours"], height=560)
    export = table.copy()
    export["Last Login"] = export["Last Login"].map(lambda v: fmt_date(v, with_time=True))
    st.download_button("Download Employee Access Report", csv_bytes(export),
                       file_name=f"employee_access_{period_start:%Y%m%d}_{period_end:%Y%m%d}.csv", mime="text/csv")


def mandatory_rows_for(emp_key):
    return mand_long[mand_long["Emp Key"] == emp_key].sort_values("Slot")


def page_profiles():
    section("Employee Profiles")
    search = st.text_input("Search employee", placeholder="Type a name, email or user ID",
                           key="profile_search").strip()
    pool = scope.sort_values("Employee Name")
    if search:
        mask = pd.Series(False, index=pool.index)
        for col in ["Employee Name", "Email", "Unique User ID"]:
            mask |= pool[col].astype(str).str.contains(search, case=False, regex=False, na=False)
        pool = pool[mask]
    if pool.empty:
        st.info("No employees match this search.")
        return
    labels = {}
    for key, name, dept, email in pool[["Emp Key", "Employee Name", "Department", "Email"]].itertuples(
            index=False, name=None):
        labels[key] = f"{name} — {dept}" + (f" · {email}" if isinstance(email, str) else "")
    selected = st.selectbox("Select employee", list(labels.keys()), format_func=lambda k: labels.get(k, k),
                            key="profile_select")
    emp = master[master["Emp Key"] == selected].iloc[0]

    st.markdown(f'<div class="employee-name">{esc(emp["Employee Name"])}</div>', unsafe_allow_html=True)
    subtitle = " · ".join(str(x) for x in [emp["Department"], emp["Business Title"]] if not is_missing(x))
    st.markdown(f'<div class="employee-sub">{esc(subtitle)}</div>', unsafe_allow_html=True)

    def info(label, value_html):
        return (f'<div class="info-item"><div class="info-label">{esc(label)}</div>'
                f'<div class="info-value">{value_html}</div></div>')

    def val(v):
        return esc(v) if not is_missing(v) and str(v).strip() else "—"

    items = [
        info("Department", val(emp["Department"])),
        info("Business Title", val(emp["Business Title"])),
        info("Email", val(emp["Email"])),
        info("Unique User ID", val(emp["Unique User ID"])),
        info("Login Status", badge(emp["Login Status"])),
        info("Last Login", esc(fmt_date(emp["Last Login"], with_time=True))),
        info("Days Logged In", esc(fmt_int(emp["Days Logged In"]))),
        info("Total Learning Hours", esc(fmt_hours(emp["Learning Hours"]))),
        info("Course Activity", badge(emp["Course Activity Status"])),
    ]
    st.markdown('<div class="info-grid">' + "".join(items) + "</div>", unsafe_allow_html=True)
    if not bool(emp["In Learner Management"]):
        st.caption("This employee does not appear in LearnerManagement, so login status cannot be verified.")

    section("Mandatory Courses")
    slots = lookup.get(dept_key(emp["Department"]))
    if not is_configured(slots):
        st.warning(NOT_CONFIGURED)
        st.caption("An administrator can configure the department's three courses in "
                   "Mandatory Program → Administrator Configuration.")
    else:
        rows = mandatory_rows_for(selected)
        done = int((rows["Completion Status"] == COMPLETED).sum())
        m = st.columns(3)
        kpi(m[0], "Mandatory Courses Completed", f"{done} / 3")
        kpi(m[1], "Mandatory Courses Remaining", f"{3 - done}", accent=GOLD)
        kpi(m[2], "Mandatory Completion", fmt_pct(done / 3 * 100))
        table = rows[["Required Course", "Completion Status", "Progress", "Matched By", "Source"]].rename(
            columns={"Required Course": "Course Name", "Progress": "Progress Percentage"})
        show_table(table, status_cols=["Completion Status"], pct_cols=["Progress Percentage"])
        if not det_ok:
            st.caption("LearnerDetail is not available, so course progress cannot be verified (status 'Unknown').")
        else:
            st.caption("'Not Started' with no progress value means the course has no record in LearnerDetail "
                       "for this period.")

    section("All Courses")
    if not det_ok:
        st.info("LearnerDetail has not been uploaded, so course details are not available.")
        return
    ec = det[(det["Emp Key"] == selected)] if (det is not None and not det.empty) else pd.DataFrame()
    courses = ec[ec["Is Course"]] if not ec.empty else ec
    if courses.empty:
        st.info("No course activity appears in the available LearnerDetail report. "
                "The employee may still have logged in.")
    else:
        courses = courses.sort_values(["Status Rank", "Last Viewed"], ascending=[False, False], na_position="last")
        table = courses[["Course Name", "Content Type", "Status", "Progress", "Learning Hours", "Started Date",
                         "Last Viewed", "Completed Date"]].rename(columns={
                             "Status": "Completion Status", "Progress": "Percent Completed",
                             "Learning Hours": "Hours Viewed", "Last Viewed": "Last Viewed Date"})
        show_table(table, status_cols=["Completion Status"], pct_cols=["Percent Completed"],
                   hour_cols=["Hours Viewed"], date_cols=["Started Date", "Last Viewed Date", "Completed Date"])
        export = table.copy()
        for c in ["Started Date", "Last Viewed Date", "Completed Date"]:
            export[c] = export[c].map(fmt_date)
        st.download_button("Download Employee Course Details", csv_bytes(export),
                           file_name=f"courses_{slug(emp['Employee Name'])}.csv", mime="text/csv")
    other = ec[~ec["Is Course"]] if not ec.empty else ec
    if not other.empty:
        with st.expander(f"Other learning content ({len(other):,}) — videos, articles, paths; not counted as courses"):
            ot = other[["Course Name", "Content Type", "Status", "Progress", "Learning Hours", "Last Viewed"]].rename(
                columns={"Course Name": "Content Name", "Status": "Completion Status", "Progress": "Percent Completed",
                         "Learning Hours": "Hours Viewed", "Last Viewed": "Last Viewed Date"})
            show_table(ot, status_cols=["Completion Status"], pct_cols=["Percent Completed"],
                       hour_cols=["Hours Viewed"], date_cols=["Last Viewed Date"])


def page_mandatory():
    tab_dept, tab_course, tab_admin = st.tabs(["Department Progress", "Course Completion Details",
                                               "Administrator Configuration"])
    scope_depts = sorted(scope["Department"].unique().tolist())

    with tab_dept:
        section("Mandatory Program by Department")
        if not det_ok:
            st.warning("LearnerDetail is not available — mandatory progress cannot be verified.")
        rows = []
        for d in scope_depts:
            slots = lookup.get(dept_key(d))
            total = int((scope["Department"] == d).sum())
            if is_configured(slots):
                me = mand_emp_scope[mand_emp_scope["Department"] == d]
                done = int(me["All Mandatory Completed"].sum())
                rows.append({"Department": d, "Status": CONFIGURED,
                             "Required Courses": " | ".join(slot_label(s) for s in slots),
                             "Total Employees": total, "Completed Employees": done,
                             "Employees Not Completed": total - done, "Completion Rate": pct(done, total)})
            else:
                rows.append({"Department": d, "Status": NOT_CONFIGURED, "Required Courses": "—",
                             "Total Employees": total, "Completed Employees": float("nan"),
                             "Employees Not Completed": float("nan"), "Completion Rate": float("nan")})
        dept_table = pd.DataFrame(rows)
        show_table(dept_table, status_cols=["Status"], pct_cols=["Completion Rate"],
                   int_cols=["Total Employees", "Completed Employees", "Employees Not Completed"])

        configured_in_scope = [d for d in scope_depts if is_configured(lookup.get(dept_key(d)))]
        if not configured_in_scope:
            st.info(f"{NOT_CONFIGURED}. Set three courses per department in Administrator Configuration.")
        else:
            section("Employee Mandatory Completion")
            d = st.selectbox("Department", configured_in_scope, key="mand_matrix_dept")
            long = mand_long_scope[mand_long_scope["Department"] == d]
            slots = lookup.get(dept_key(d))
            matrix = (long.pivot_table(index=["Emp Key", "Employee Name", "Email"], columns="Slot",
                                       values="Completion Status", aggfunc="first").reset_index())
            rename = {i: f"{i}. {slot_label(slots[i - 1])}" for i in (1, 2, 3)}
            matrix = matrix.rename(columns=rename)
            for col in rename.values():
                if col not in matrix.columns:
                    matrix[col] = None
            me = mand_emp_scope.set_index("Emp Key")
            matrix["Completed"] = matrix["Emp Key"].map(me["Mandatory Completed"]).map(lambda v: f"{int(v)} / 3")
            matrix["Remaining"] = matrix["Emp Key"].map(me["Mandatory Remaining"])
            matrix["Completion %"] = matrix["Emp Key"].map(me["Mandatory %"])
            matrix = matrix.drop(columns=["Emp Key"]).rename(columns={"Employee Name": "Employee"})
            matrix = matrix.sort_values(["Completion %", "Employee"], ascending=[False, True])
            show_table(matrix, status_cols=list(rename.values()), pct_cols=["Completion %"],
                       int_cols=["Remaining"], height=480)
            st.download_button("Download Mandatory Progress", csv_bytes(matrix),
                               file_name=f"mandatory_progress_{slug(d)}.csv", mime="text/csv")

    with tab_course:
        section("Who Completed Each Mandatory Course")
        configured_in_scope = [d for d in scope_depts if is_configured(lookup.get(dept_key(d)))]
        if not configured_in_scope:
            st.info(NOT_CONFIGURED)
        else:
            c1, c2, c3 = st.columns([1.2, 1.8, 1])
            with c1:
                d = st.selectbox("Department", configured_in_scope, key="mand_course_dept")
            slots = lookup.get(dept_key(d))
            with c2:
                slot_no = st.selectbox("Mandatory course", [1, 2, 3],
                                       format_func=lambda i: f"{i}. {slot_label(slots[i - 1])}",
                                       key=f"mand_course_slot_{slug(d)}")
            with c3:
                show = st.selectbox("Show", ["All employees", "Completed", "Not completed"], key="mand_course_show")
            rows = mand_long_scope[(mand_long_scope["Department"] == d) & (mand_long_scope["Slot"] == slot_no)]
            done_n = int((rows["Completion Status"] == COMPLETED).sum())
            m = st.columns(3)
            kpi(m[0], "Completed", fmt_int(done_n))
            kpi(m[1], "Not Completed", fmt_int(len(rows) - done_n), accent=GOLD)
            kpi(m[2], "Completion Rate", fmt_pct(pct(done_n, len(rows))))
            if show == "Completed":
                rows = rows[rows["Completion Status"] == COMPLETED]
            elif show == "Not completed":
                rows = rows[rows["Completion Status"] != COMPLETED]
            table = rows[["Employee Name", "Email", "Completion Status", "Progress", "Matched Course", "Matched By",
                          "Source"]].rename(columns={"Employee Name": "Employee", "Progress": "Progress Percentage"})
            table = table.sort_values(["Completion Status", "Employee"])
            show_table(table, status_cols=["Completion Status"], pct_cols=["Progress Percentage"], height=460)
            st.download_button("Download Course Completion List", csv_bytes(table),
                               file_name=f"mandatory_course_{slug(d)}_{slot_no}.csv", mime="text/csv")

    with tab_admin:
        render_admin()


def render_admin():
    section("Administrator Configuration")
    st.caption("Each department has its own three mandatory courses. Courses are matched by Course ID when the "
               "report provides one; otherwise by exact course name (case and spacing normalised). "
               "Similar titles are never treated as the same course.")
    flash = st.session_state.pop("cfg_flash", None)
    if flash:
        st.success(flash)
    cfg = st.session_state["mandatory_config"]
    cfg_lookup = config_lookup(cfg)
    known_keys = {dept_key(d) for d in departments}
    extra_cfg = [k for k in cfg if dept_key(k) not in known_keys]
    dept_options = departments + extra_cfg
    catalog = course_catalog(det, raw.get("content"))
    manual = "✎ Enter course name / ID manually"

    sel_dept = st.selectbox("Department to configure", dept_options, key="cfg_dept")
    current = cfg_lookup.get(dept_key(sel_dept)) or empty_slots()
    ver = st.session_state["cfg_version"]
    dk = slug(dept_key(sel_dept))
    status_now = CONFIGURED if is_configured(current) else NOT_CONFIGURED
    st.markdown(f"Current status: {badge(status_now)}", unsafe_allow_html=True)
    if not catalog:
        st.caption("Upload LearnerDetail or ContentSummary to choose courses from the report catalog.")

    new_slots = []
    cols = st.columns(3)
    for i in range(3):
        with cols[i]:
            st.markdown(f"**Mandatory Course {i + 1}**")
            cur = current[i]
            options = [manual] + list(catalog.keys())
            cur_label = catalog_label_for(catalog, cur)
            index = options.index(cur_label) if cur_label in options else 0
            choice = st.selectbox("Course", options, index=index, key=f"cfg_sel_{dk}_{i}_{ver}")
            if choice == manual:
                name = st.text_input("Course name", value=cur.get("name", ""), key=f"cfg_name_{dk}_{i}_{ver}")
                cid = st.text_input("Course ID (recommended)", value=cur.get("course_id", ""),
                                    key=f"cfg_id_{dk}_{i}_{ver}")
            else:
                rec = catalog[choice]
                name, cid = rec["name"], rec["course_id"]
                st.caption(f"Course ID: {cid or 'not provided in the reports'}")
            new_slots.append({"name": (name or "").strip(), "course_id": (cid or "").strip()})

    b1, b2, _ = st.columns([1.2, 1.2, 3])
    with b1:
        save = st.button("Save Department Courses", type="primary", key=f"cfg_save_{dk}")
    with b2:
        clear = st.button("Clear Department Courses", key=f"cfg_clear_{dk}")
    if save:
        identities = [(s["course_id"].casefold() or "") + "|" + norm_title(s["name"]) for s in new_slots]
        if not all(slot_filled(s) for s in new_slots):
            st.error("Enter all three mandatory courses before saving.")
        elif len(set(identities)) < 3:
            st.error("The three mandatory courses must be different.")
        else:
            for k in [k for k in cfg if dept_key(k) == dept_key(sel_dept)]:
                cfg.pop(k)
            cfg[sel_dept] = new_slots
            st.session_state["cfg_flash"] = f"Mandatory courses saved for {sel_dept} (this session)."
            st.rerun()
    if clear:
        for k in [k for k in cfg if dept_key(k) == dept_key(sel_dept)]:
            cfg.pop(k)
        st.session_state["cfg_version"] += 1
        st.session_state["cfg_flash"] = f"Mandatory courses cleared for {sel_dept}."
        st.rerun()

    section("Configured Courses by Department")
    rows = []
    for d in dept_options:
        slots = cfg_lookup.get(dept_key(d)) or empty_slots()
        rows.append({"Department": d, "Status": CONFIGURED if is_configured(slots) else NOT_CONFIGURED,
                     "Course 1": slot_label(slots[0]), "Course 2": slot_label(slots[1]),
                     "Course 3": slot_label(slots[2]),
                     "In Current Reports": "Yes" if dept_key(d) in known_keys else "No"})
    show_table(pd.DataFrame(rows), status_cols=["Status"])

    payload = {"application": "Al Bawani Learning Hub", "format_version": 2,
               "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "departments": cfg}
    st.download_button("Export Configuration (JSON)",
                       json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name=f"albawani_mandatory_courses_{date.today():%Y%m%d}.json",
                       mime="application/json")
    st.info("This configuration is kept only for the current browser session — it is not saved permanently. "
            "Export the JSON file and import it from the sidebar (Mandatory Course Configuration) next time.")


def page_analytics():
    section("Course Analytics")
    if not det_ok or det_scope is None or det_scope.empty:
        st.info("Upload LearnerDetail to see course analytics.")
    else:
        types = sorted(det_scope["Content Type"].unique().tolist())
        default_types = ["Course"] if "Course" in types else types
        c1, c2 = st.columns([1, 2])
        with c1:
            sel_types = st.multiselect("Content Type", types, default=default_types, key="ca_types")
        data = det_scope[det_scope["Content Type"].isin(sel_types)] if sel_types else det_scope
        with c2:
            course_names = sorted(data["Course Name"].unique().tolist())
            sel_courses = st.multiselect("Course", course_names, default=[], placeholder="All courses",
                                         key="ca_courses")
        if sel_courses:
            data = data[data["Course Name"].isin(sel_courses)]
        if data.empty:
            st.info("No records match these filters.")
        else:
            agg = (data.groupby("Course Key")
                   .agg(**{"Course Name": ("Course Name", "first"),
                           "Content Type": ("Content Type", "first"),
                           "Unique Learners": ("Emp Key", "nunique"),
                           "Completed": ("Status", lambda s: int((s == COMPLETED).sum())),
                           "In Progress": ("Status", lambda s: int((s == IN_PROGRESS).sum())),
                           "Not Started": ("Status", lambda s: int((s == NOT_STARTED).sum())),
                           "Unknown": ("Status", lambda s: int((s == UNKNOWN).sum())),
                           "Learning Hours": ("Learning Hours", lambda s: s.sum(min_count=1))})
                   .reset_index(drop=True))
            agg["Completions"] = agg["Completed"].where(agg["Content Type"] == "Course")
            agg["Completion Rate"] = (agg["Completed"] / agg["Unique Learners"] * 100).where(
                agg["Content Type"] == "Course")
            agg = agg.sort_values(["Unique Learners", "Course Name"], ascending=[False, True])
            courses_only = data[data["Is Course"]]
            m = st.columns(3)
            kpi(m[0], "Content Items", fmt_int(len(agg)))
            kpi(m[1], "Unique Learners", fmt_int(data["Emp Key"].nunique()))
            kpi(m[2], "Course Completions", fmt_int(int((courses_only["Status"] == COMPLETED).sum())),
                "Courses only")
            table = agg[["Course Name", "Content Type", "Unique Learners", "Completions", "Completion Rate",
                         "In Progress", "Not Started", "Unknown", "Learning Hours"]]
            show_table(table, pct_cols=["Completion Rate"], hour_cols=["Learning Hours"],
                       int_cols=["Unique Learners", "Completions", "In Progress", "Not Started", "Unknown"],
                       height=420)
            st.caption("Completions are counted for courses only; videos, articles and learning paths show '—'.")
            st.download_button("Download Course Analytics", csv_bytes(table), file_name="course_analytics.csv",
                               mime="text/csv")

            top = agg.head(15)
            dist = top.melt(id_vars=["Course Name"], value_vars=["Completed", "In Progress", "Not Started", "Unknown"],
                            var_name="Completion Status", value_name="Learners")
            dist = dist[dist["Learners"] > 0]
            if not dist.empty:
                fig = px.bar(dist, y="Course Name", x="Learners", color="Completion Status", orientation="h",
                             color_discrete_map=STATUS_COLORS, category_orders={"Completion Status": STATUS_ORDER})
                fig.update_layout(barmode="stack", xaxis_title="Learners", yaxis_title="")
                fig.update_yaxes(categoryorder="total ascending")
                plot(style_fig(fig, "Completion Status Distribution (top 15 by learners)",
                               height=max(320, 30 * top.shape[0] + 140)))

    content_raw = raw.get("content")
    if content_raw is not None and not content_raw.empty:
        with st.expander("Content Summary report"):
            st.dataframe(content_raw, use_container_width=True, hide_index=True)
    group_raw = raw.get("group")
    if group_raw is not None and not group_raw.empty:
        with st.expander("Group Summary report"):
            st.dataframe(group_raw, use_container_width=True, hide_index=True)
    rec_s, rec_d = raw.get("rec_summary"), raw.get("rec_detail")
    if uploads.get("rec_summary") is not None or uploads.get("rec_detail") is not None:
        with st.expander("Recommendations"):
            shown = False
            for label, frame in [("RecommendationSummary", rec_s), ("RecommendationDetail", rec_d)]:
                if frame is not None and not frame.empty:
                    st.markdown(f"**{label}**")
                    st.dataframe(frame, use_container_width=True, hide_index=True)
                    shown = True
            if not shown:
                st.caption("No recommendation records are available in this reporting period.")


def page_history():
    section("Monthly History")
    for lvl, msg in archive_notes:
        if lvl == "error":
            st.error(msg)
        elif lvl == "warn":
            st.warning(msg)
    snapshot = build_snapshot(master, det, det_ok, period_label, period_start, period_end)
    parts = []
    dup_period = archive is not None and period_label in set(archive["Period"])
    replace = False
    if dup_period:
        st.warning(f"The archive already contains records for '{period_label}'. They are kept unchanged.")
        replace = st.checkbox("Replace the archived records for this period with the current reports",
                              value=False, key="hist_replace")
    if archive is not None:
        parts.append(archive[archive["Period"] != period_label] if replace else archive)
    if not dup_period or replace:
        parts.append(snapshot)
    hist = pd.concat(parts, ignore_index=True) if parts else snapshot
    hist["Course Key"] = hist["Course Key"].astype(object).where(hist["Course Key"].notna(), "")
    hist = hist.drop_duplicates(["Record Type", "Period", "Email Key", "Course Key"], keep="first")
    hist["Course Key"] = hist["Course Key"].replace("", None)

    view = hist
    if dept_filter != ALL_DEPTS:
        target = dept_key(dept_filter)
        view = hist[hist["Department"].map(lambda v: dept_key(v) == target if not is_missing(v) else False)]
        st.caption(f"Filtered to {dept_filter}. Archived rows without a department are not included.")

    metrics = period_metrics(view) if not view.empty else pd.DataFrame()
    m = st.columns(3)
    kpi(m[0], "Reporting Periods", fmt_int(hist["Period"].nunique()))
    kpi(m[1], "Current Period", period_label)
    kpi(m[2], "Historical Records", fmt_int(len(hist)))

    if not metrics.empty:
        section("Period Comparison")
        show_table(metrics, int_cols=["Employees", "Logged In", "No Login During Selected Period", "Course Learners",
                                      "Course Completions"], hour_cols=["Learning Hours"])
        chart = metrics.melt(id_vars="Period", value_vars=["Logged In", "Course Completions"],
                             var_name="Measure", value_name="Value").dropna()
        if not chart.empty and metrics["Period"].nunique() > 1:
            fig = px.bar(chart, x="Period", y="Value", color="Measure", barmode="group",
                         color_discrete_map={"Logged In": GREEN, "Course Completions": GOLD},
                         category_orders={"Period": metrics["Period"].tolist()})
            fig.update_layout(xaxis_title="", yaxis_title="")
            plot(style_fig(fig, "Logins and Course Completions by Period"))

        periods = metrics["Period"].tolist()
        if len(periods) > 1:
            c1, c2 = st.columns(2)
            with c1:
                pa = st.selectbox("Compare period", periods, index=len(periods) - 2, key="hist_a")
            with c2:
                pb = st.selectbox("With period", periods, index=len(periods) - 1, key="hist_b")
            ra = metrics.set_index("Period").loc[pa]
            rb = metrics.set_index("Period").loc[pb]
            comp = []
            for col in ["Employees", "Logged In", "No Login During Selected Period", "Course Learners",
                        "Course Completions", "Learning Hours"]:
                a, b = ra[col], rb[col]
                change = (b - a) if not (is_missing(a) or is_missing(b)) else float("nan")
                comp.append({"Measure": col, pa: a, pb: b, "Change": change})
            comp_df = pd.DataFrame(comp)
            if pa == pb:
                comp_df = comp_df[["Measure", pa]]
            show_table(comp_df, hour_cols=[pa, pb, "Change"] if pa != pb else [pa])
        else:
            st.caption("Upload a previous history archive in the sidebar to compare reporting periods.")

    section("Historical Records")
    c1, c2 = st.columns(2)
    with c1:
        rtype = st.selectbox("Record type", ["Employee Access", "Course"], key="hist_type")
    with c2:
        period_options = ["All periods"] + ordered_periods(hist)
        psel = st.selectbox("Period", period_options, key="hist_period")
    rec = view[view["Record Type"] == rtype]
    if psel != "All periods":
        rec = rec[rec["Period"] == psel]
    if rtype == "Employee Access":
        cols = ["Period", "Employee Name", "Department", "Login Status", "Days Logged In", "Course Activity Status",
                "Courses Completed", "Learning Hours"]
    else:
        cols = ["Period", "Employee Name", "Department", "Course Name", "Content Type", "Status", "Progress",
                "Learning Hours", "Completed Date"]
    show_table(rec[cols], status_cols=["Login Status", "Course Activity Status", "Status"], pct_cols=["Progress"],
               int_cols=["Days Logged In", "Courses Completed"], hour_cols=["Learning Hours"], height=420)
    st.download_button("Download Updated History Archive", csv_bytes(hist[HISTORY_COLUMNS]),
                       file_name="al_bawani_learning_history.csv", mime="text/csv")
    st.caption("Keep this archive and upload it next month. Existing periods are never overwritten unless you "
               "choose to replace them.")


PAGE_RENDERERS = {
    "Overview": page_overview,
    "Employee Access": page_access,
    "Employee Profiles": page_profiles,
    "Mandatory Program": page_mandatory,
    "Course Analytics": page_analytics,
    "Monthly History": page_history,
}
PAGE_RENDERERS.get(page, page_overview)()

st.markdown('<div class="ab-footer">AL BAWANI | LEARNING &amp; DEVELOPMENT</div>', unsafe_allow_html=True)
