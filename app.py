
import io
from pathlib import Path
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

# ==================================================
# AL BAWANI | LEARNING & DEVELOPMENT
# ==================================================

st.set_page_config(
    page_title="Al Bawani | Learning Hub",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

GREEN = "#08783E"
DARK_GREEN = "#075B32"
GOLD = "#C6A45B"

# ==================================================
# CUSTOM DESIGN
# ==================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #F4F7F5;
    color: #20352A;
}

[data-testid="stSidebar"] {
    background: white;
    border-right: 1px solid #E4EBE6;
}

[data-testid="stMetric"] {
    background: white;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #E4ECE6;
    box-shadow: 0 4px 16px rgba(20,60,40,.05);
    transition: all .25s ease;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 9px 22px rgba(8,120,62,.12);
}

[data-testid="stMetricLabel"] {
    color: #718078;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #075B32;
    font-weight: 800;
}

.hero {
    background: linear-gradient(115deg,#064D2B,#08783E,#2A9B60);
    padding: 34px;
    border-radius: 20px;
    color: white;
    margin: 15px 0 25px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 28px rgba(8,120,62,.16);
}

.hero h1 {
    color: white;
    font-size: 30px;
    font-weight: 800;
    margin: 0;
}

.hero p {
    color: #E5F3EA;
    margin-top: 10px;
}

.section-title {
    color: #17452F;
    font-size: 20px;
    font-weight: 750;
    margin: 20px 0 12px;
}

.stButton button,
.stDownloadButton button {
    border-radius: 9px;
    font-weight: 650;
    transition: all .2s ease;
}

.stButton button:hover,
.stDownloadButton button:hover {
    transform: translateY(-2px);
    border-color: #08783E;
}

div[data-testid="stTabs"] button {
    font-weight: 650;
}

#MainMenu, footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# ==================================================
# DATA FUNCTIONS
# ==================================================

def read_report(file):
    if file is None:
        return None

    raw = file.getvalue()
    name = file.name.lower()

    try:
        if name.endswith(".csv"):
            try:
                return pd.read_csv(
                    io.BytesIO(raw),
                    encoding="utf-8-sig"
                )
            except UnicodeDecodeError:
                return pd.read_csv(
                    io.BytesIO(raw),
                    encoding="latin1"
                )

        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(
                io.BytesIO(raw),
                sheet_name=0
            )

    except Exception as error:
        st.error(f"Could not read {file.name}: {error}")

    return None


def clean_text(series):
    return series.fillna("").astype(str).str.strip()


def parse_progress(series):
    values = (
        series.fillna("0")
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(
        values,
        errors="coerce"
    ).fillna(0).clip(0, 100)


def parse_hours(value):
    if pd.isna(value):
        return 0.0

    try:
        parts = str(value).strip().split(":")

        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
            return hours + minutes / 60 + seconds / 3600

        if len(parts) == 2:
            minutes, seconds = map(float, parts)
            return minutes / 60 + seconds / 3600

        return float(value)

    except (ValueError, TypeError):
        return 0.0


def get_status(progress):
    if progress >= 100:
        return "Completed"
    elif progress > 0:
        return "In Progress"
    return "Not Started"


def prepare_summary(data):
    df = data.copy()

    required = ["Name", "Email"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            "Learner Summary is missing: " + ", ".join(missing)
        )

    df["Name"] = clean_text(df["Name"])
    df["Email"] = clean_text(df["Email"]).str.lower()

    department_col = next(
        (c for c in df.columns if c.lower() == "department"),
        None
    )

    if department_col:
        df["Department"] = clean_text(df[department_col])
    else:
        df["Department"] = "Not Specified"

    df["Department"] = df["Department"].replace(
        "", "Not Specified"
    )

    for col in [
        "Days Logged In",
        "Course Views",
        "Course Completions"
    ]:
        if col not in df.columns:
            df[col] = 0

        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        ).fillna(0)

    if "Hours Viewed" in df.columns:
        df["Learning Hours"] = (
            df["Hours Viewed"].apply(parse_hours)
        )
    else:
        df["Learning Hours"] = 0.0

    df = df.drop_duplicates(
        subset=["Email"],
        keep="last"
    )

    return df


def prepare_detail(data):
    df = data.copy()

    required = ["Name", "Email", "Content Name"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            "Learner Detail is missing: " + ", ".join(missing)
        )

    df["Name"] = clean_text(df["Name"])
    df["Email"] = clean_text(df["Email"]).str.lower()
    df["Content Name"] = clean_text(df["Content Name"])

    if "Content Type" in df.columns:
        df = df[
            df["Content Type"].astype(str).str.lower() == "course"
        ].copy()

    if "Percent Completed" in df.columns:
        df["Progress"] = parse_progress(
            df["Percent Completed"]
        )
    else:
        df["Progress"] = 0

    df["Status"] = df["Progress"].apply(get_status)

    if "Content ID" in df.columns:
        content_id = clean_text(df["Content ID"])

        df["Course Key"] = content_id.where(
            content_id != "",
            df["Content Name"].str.lower()
        )
    else:
        df["Course Key"] = df["Content Name"].str.lower()

    df = df.sort_values("Progress", ascending=False)

    df = df.drop_duplicates(
        subset=["Email", "Course Key"],
        keep="first"
    )

    return df


def csv_download(data):
    return data.to_csv(
        index=False
    ).encode("utf-8-sig")


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.markdown(
        f"""
        <div style="text-align:center;padding:10px;">
            <h2 style="color:{GREEN};margin-bottom:0;">
                LEARNING HUB
            </h2>
            <small style="letter-spacing:2px;color:#84928A;">
                AL BAWANI
            </small>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("### LinkedIn Learning Reports")

    summary_file = st.file_uploader(
        "Learner Summary",
        type=["csv", "xlsx", "xls"],
        key="summary"
    )

    detail_file = st.file_uploader(
        "Learner Detail",
        type=["csv", "xlsx", "xls"],
        key="detail"
    )

    group_file = st.file_uploader(
        "Group Summary (Optional)",
        type=["csv", "xlsx", "xls"],
        key="group"
    )

    recommendation_file = st.file_uploader(
        "Recommendation Summary (Optional)",
        type=["csv", "xlsx", "xls"],
        key="recommendation"
    )

    st.divider()

    st.markdown("### Reporting Period")

    period = st.text_input(
        "Report Month",
        value=date.today().strftime("%b %Y")
    ).strip()

    st.divider()

    st.markdown("### Mandatory Courses")

    mandatory_courses = []

    for i in range(1, 4):
        course = st.text_input(
            f"Mandatory Course {i}",
            placeholder="Enter official course name",
            key=f"course_{i}"
        )
        mandatory_courses.append(course.strip())

    st.divider()

    st.markdown("### Historical Archive")

    archive_file = st.file_uploader(
        "Previous Tracking Archive",
        type=["csv"],
        key="archive"
    )

    st.caption(
        "Download the archive after each reporting period "
        "and upload it again next month."
    )


# ==================================================
# HEADER - FIXED HTML RENDERING
# ==================================================

logo_path = Path("AL-Bawani-logo.png")

left, right = st.columns([1.4, 5], vertical_alignment="center")

with left:
    if logo_path.exists():
        st.image(
            str(logo_path),
            width=180
        )
    else:
        st.markdown(
            f"<h2 style='color:{GREEN}'>AL BAWANI</h2>",
            unsafe_allow_html=True
        )

with right:
    st.markdown("""
    <div style="padding-top:8px;">
        <div style="font-size:11px;color:#7A8980;
        letter-spacing:2px;font-weight:800;">
            PEOPLE DEVELOPMENT
        </div>

        <div style="font-size:26px;font-weight:800;
        color:#17452F;">
            Learning &amp; Development Dashboard
        </div>

        <div style="font-size:13px;color:#829087;">
            Employee Learning Performance &amp; Training Tracking
        </div>
    </div>
    """, unsafe_allow_html=True)


st.markdown("""
<div class="hero">
    <h1>Build Skills. Grow Together.</h1>
    <p>
        Monitor employee learning journeys,
        mandatory training and professional development.
    </p>
</div>
""", unsafe_allow_html=True)


# ==================================================
# LOAD FILES
# ==================================================

summary_raw = read_report(summary_file)
detail_raw = read_report(detail_file)
group_data = read_report(group_file)
recommendation_data = read_report(recommendation_file)

if summary_raw is None or detail_raw is None:

    st.info(
        "Upload Learner Summary and Learner Detail "
        "to activate the dashboard."
    )

    a, b, c = st.columns(3)

    a.info("Employee Insights\n\nTrack employee activity.")
    b.info("Course Progress\n\nMonitor course completion.")
    c.info("Learning Analytics\n\nReview training performance.")

    st.stop()


try:
    summary = prepare_summary(summary_raw)
    detail = prepare_detail(detail_raw)

except ValueError as error:
    st.error(str(error))
    st.stop()


employee_emails = set(summary["Email"])

detail = detail[
    detail["Email"].isin(employee_emails)
].copy()


# ==================================================
# FILTERS
# ==================================================

st.markdown(
    '<div class="section-title">Dashboard Filters</div>',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

departments = sorted(
    summary["Department"].dropna().unique().tolist()
)

with col1:
    selected_department = st.selectbox(
        "Department",
        ["All Departments"] + departments
    )

with col2:
    employee_search = st.text_input(
        "Search Employee",
        placeholder="Name or email"
    )


filtered_summary = summary.copy()

if selected_department != "All Departments":
    filtered_summary = filtered_summary[
        filtered_summary["Department"] == selected_department
    ]

if employee_search:
    filtered_summary = filtered_summary[
        filtered_summary["Name"].str.contains(
            employee_search,
            case=False,
            na=False
        )
        |
        filtered_summary["Email"].str.contains(
            employee_search,
            case=False,
            na=False
        )
    ]


filtered_emails = set(filtered_summary["Email"])

filtered_detail = detail[
    detail["Email"].isin(filtered_emails)
].copy()


# ==================================================
# KPI CARDS
# ==================================================

st.markdown(
    '<div class="section-title">Learning Overview</div>',
    unsafe_allow_html=True
)

total_employees = filtered_summary["Email"].nunique()
total_views = int(filtered_summary["Course Views"].sum())
total_completions = int(filtered_summary["Course Completions"].sum())
total_hours = float(filtered_summary["Learning Hours"].sum())

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Employees", f"{total_employees:,}")
k2.metric("Course Views", f"{total_views:,}")
k3.metric("Course Completions", f"{total_completions:,}")
k4.metric("Learning Hours", f"{total_hours:,.1f} h")


# ==================================================
# DASHBOARD TABS
# ==================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "Employee Tracking",
    "Course Analytics",
    "Mandatory Program",
    "Monthly History"
])


# ==================================================
# TAB 1: OVERVIEW
# ==================================================

with tab1:

    st.markdown("### Learning Performance")

    chart1, chart2 = st.columns(2)

    with chart1:

        department_data = (
            filtered_summary.groupby(
                "Department",
                as_index=False
            )
            .agg(
                Completions=("Course Completions", "sum")
            )
            .sort_values(
                "Completions",
                ascending=False
            )
        )

        fig = px.bar(
            department_data,
            x="Department",
            y="Completions",
            color_discrete_sequence=[GREEN],
            title="Course Completions by Department"
        )

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis_title="",
            yaxis_title="Completions"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with chart2:

        status_data = (
            filtered_detail["Status"]
            .value_counts()
            .reindex(
                ["Completed", "In Progress", "Not Started"],
                fill_value=0
            )
            .rename_axis("Status")
            .reset_index(name="Courses")
        )

        fig = px.pie(
            status_data,
            names="Status",
            values="Courses",
            hole=0.65,
            title="Course Status Distribution",
            color="Status",
            color_discrete_map={
                "Completed": GREEN,
                "In Progress": GOLD,
                "Not Started": "#C9D3CD"
            }
        )

        fig.update_layout(
            paper_bgcolor="white"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.markdown("### Department Summary")

    department_table = (
        filtered_summary.groupby(
            "Department",
            as_index=False
        )
        .agg(
            Employees=("Email", "nunique"),
            Course_Views=("Course Views", "sum"),
            Completions=("Course Completions", "sum"),
            Learning_Hours=("Learning Hours", "sum")
        )
    )

    department_table["Learning_Hours"] = (
        department_table["Learning_Hours"].round(1)
    )

    st.dataframe(
        department_table,
        use_container_width=True,
        hide_index=True
    )

    if group_data is not None and not group_data.empty:
        st.markdown("### LinkedIn Group Summary")

        st.dataframe(
            group_data,
            use_container_width=True,
            hide_index=True
        )


# ==================================================
# TAB 2: EMPLOYEE TRACKING
# ==================================================

with tab2:

    st.markdown("### Employee Directory")

    employee_table = filtered_summary[[
        "Name",
        "Email",
        "Department",
        "Days Logged In",
        "Course Views",
        "Course Completions",
        "Learning Hours"
    ]].copy()

    employee_table["Learning Hours"] = (
        employee_table["Learning Hours"].round(1)
    )

    st.dataframe(
        employee_table,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Employee Profile")

    employee_names = sorted(
        filtered_summary["Name"].dropna().unique().tolist()
    )

    if employee_names:

        selected_employee = st.selectbox(
            "Select Employee",
            employee_names
        )

        employee = filtered_summary[
            filtered_summary["Name"] == selected_employee
        ].iloc[0]

        employee_email = employee["Email"]

        employee_courses = filtered_detail[
            filtered_detail["Email"] == employee_email
        ].copy()

        p1, p2, p3 = st.columns(3)

        p1.metric(
            "Course Views",
            int(employee["Course Views"])
        )

        p2.metric(
            "Completions",
            int(employee["Course Completions"])
        )

        p3.metric(
            "Learning Hours",
            f"{employee['Learning Hours']:.1f} h"
        )

        st.caption(
            f"{employee_email} | {employee['Department']}"
        )

        if not employee_courses.empty:

            columns = [
                "Content Name",
                "Progress",
                "Status"
            ]

            if "Completed At (PST/PDT)" in employee_courses.columns:
                columns.append("Completed At (PST/PDT)")

            st.dataframe(
                employee_courses[columns].sort_values(
                    "Progress",
                    ascending=False
                ),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No course records found for this employee.")


# ==================================================
# TAB 3: COURSE ANALYTICS
# ==================================================

with tab3:

    st.markdown("### Course Analytics")

    if not filtered_detail.empty:

        course_summary = (
            filtered_detail.groupby(
                "Content Name",
                as_index=False
            )
            .agg(
                Learners=("Email", "nunique"),
                Average_Progress=("Progress", "mean"),
                Completed=(
                    "Status",
                    lambda x: (x == "Completed").sum()
                )
            )
            .sort_values(
                "Learners",
                ascending=False
            )
        )

        top_courses = (
            course_summary.head(15)
            .sort_values("Learners")
        )

        fig = px.bar(
            top_courses,
            x="Learners",
            y="Content Name",
            orientation="h",
            color="Average_Progress",
            color_continuous_scale=[
                "#DCE9E0",
                GREEN
            ],
            title="Top 15 Courses by Learners"
        )

        fig.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.dataframe(
            course_summary.round(1),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No course activity available.")

    if recommendation_data is not None:

        st.markdown("### Recommended Courses")

        if recommendation_data.empty:
            st.caption("No recommendation records in this report.")
        else:
            st.dataframe(
                recommendation_data,
                use_container_width=True,
                hide_index=True
            )


# ==================================================
# TAB 4: MANDATORY COURSES
# ==================================================

with tab4:

    st.markdown("### Mandatory Learning Program")

    configured_courses = [
        course for course in mandatory_courses if course
    ]

    if not configured_courses:

        st.info(
            "Mandatory course titles are not configured yet. "
            "Enter the official titles in the sidebar when available."
        )

    else:

        if len(configured_courses) < 3:
            st.warning(
                "Only some mandatory courses have been configured."
            )

        mandatory_rows = []

        for _, employee in filtered_summary.iterrows():

            email = employee["Email"]

            employee_detail = detail[
                detail["Email"] == email
            ]

            row = {
                "Employee": employee["Name"],
                "Department": employee["Department"]
            }

            completed_count = 0

            for i, course_title in enumerate(
                configured_courses,
                start=1
            ):

                matches = employee_detail[
                    employee_detail["Content Name"]
                    .str.strip()
                    .str.casefold()
                    == course_title.casefold()
                ]

                if matches.empty:
                    progress = 0
                else:
                    progress = float(
                        matches["Progress"].max()
                    )

                status = get_status(progress)

                if status == "Completed":
                    completed_count += 1

                row[f"Course {i}"] = status
                row[f"Progress {i}"] = progress

            row["Completed Courses"] = completed_count

            row["Program Progress"] = (
                completed_count / len(configured_courses) * 100
            )

            mandatory_rows.append(row)

        mandatory_df = pd.DataFrame(mandatory_rows)

        for i, course_title in enumerate(
            configured_courses,
            start=1
        ):

            completed = (
                mandatory_df[f"Course {i}"] == "Completed"
            ).sum()

            total = len(mandatory_df)

            st.markdown(f"**{course_title}**")

            st.progress(
                completed / total if total else 0,
                text=f"{completed} of {total} employees completed"
            )

        st.markdown("### Employee Completion Matrix")

        st.dataframe(
            mandatory_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Mandatory Tracking",
            csv_download(mandatory_df),
            file_name="al_bawani_mandatory_tracking.csv",
            mime="text/csv"
        )


# ==================================================
# TAB 5: MONTHLY HISTORY
# ==================================================

with tab5:

    st.markdown("### Monthly Learning History")

    st.caption(
        "Download the archive after each reporting period. "
        "Upload it again next month to continue tracking."
    )

    current_history = detail.copy()

    current_history["Period"] = (
        period or date.today().strftime("%b %Y")
    )

    department_lookup = summary.set_index(
        "Email"
    )["Department"].to_dict()

    current_history["Department"] = (
        current_history["Email"].map(
            department_lookup
        ).fillna("Not Specified")
    )

    current_history = current_history.rename(
        columns={"Content Name": "Course Name"}
    )

    history_columns = [
        "Period",
        "Email",
        "Name",
        "Department",
        "Course Key",
        "Course Name",
        "Progress",
        "Status"
    ]

    current_history = current_history[history_columns]

    if archive_file is not None:

        try:
            old_history = pd.read_csv(archive_file)

        except Exception as error:
            st.error(f"Could not read archive: {error}")
            old_history = pd.DataFrame(
                columns=history_columns
            )

    else:
        old_history = pd.DataFrame(
            columns=history_columns
        )

    for column in history_columns:
        if column not in old_history.columns:
            old_history[column] = ""

    old_history = old_history[history_columns]

    combined_history = pd.concat(
        [old_history, current_history],
        ignore_index=True
    )

    combined_history["Period"] = (
        combined_history["Period"].astype(str)
    )

    combined_history["Email"] = (
        combined_history["Email"].astype(str).str.lower()
    )

    combined_history["Course Key"] = (
        combined_history["Course Key"].astype(str)
    )

    combined_history = combined_history.drop_duplicates(
        subset=["Period", "Email", "Course Key"],
        keep="last"
    )

    st.metric(
        "Historical Course Records",
        f"{len(combined_history):,}"
    )

    if not combined_history.empty:

        period_summary = (
            combined_history.groupby(
                "Period",
                as_index=False
            )
            .agg(
                Employees=("Email", "nunique"),
                Course_Records=("Course Key", "count"),
                Completed=(
                    "Status",
                    lambda x: (x == "Completed").sum()
                ),
                Average_Progress=("Progress", "mean")
            )
        )

        period_summary["Average_Progress"] = (
            pd.to_numeric(
                period_summary["Average_Progress"],
                errors="coerce"
            ).round(1)
        )

        st.markdown("### Period Comparison")

        st.dataframe(
            period_summary,
            use_container_width=True,
            hide_index=True
        )

        periods = combined_history["Period"].unique().tolist()

        if len(periods) >= 2:

            trend = (
                combined_history.groupby(
                    "Period",
                    as_index=False
                )
                .agg(
                    Completed=(
                        "Status",
                        lambda x: (x == "Completed").sum()
                    )
                )
            )

            fig = px.line(
                trend,
                x="Period",
                y="Completed",
                markers=True,
                title="Completed Courses by Period",
                color_discrete_sequence=[GREEN]
            )

            fig.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        st.markdown("### Employee History")

        employee_options = sorted(
            combined_history["Name"]
            .dropna()
            .astype(str)
            .unique()
        )

        selected_history_employee = st.selectbox(
            "Select Employee",
            ["All Employees"] + employee_options,
            key="history_employee"
        )

        history_view = combined_history.copy()

        if selected_history_employee != "All Employees":
            history_view = history_view[
                history_view["Name"] == selected_history_employee
            ]

        st.dataframe(
            history_view.sort_values(
                ["Period", "Name", "Course Name"]
            ),
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download / Update Historical Archive",
            csv_download(combined_history),
            file_name="al_bawani_learning_history_archive.csv",
            mime="text/csv"
        )

    else:
        st.info("No historical records available yet.")


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center;color:#89958E;
    font-size:11px;padding:10px;">
        AL BAWANI | LEARNING & DEVELOPMENT
        <br>
        EMPLOYEE LEARNING TRACKER
    </div>
    """,
    unsafe_allow_html=True
)
