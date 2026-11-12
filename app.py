
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Al Bawani | Learning Hub",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

GREEN = "#007834"
DARK = "#17452F"
GOLD = "#C6A45B"
BG = "#F4F7F5"

# --------------------------------------------------
# CUSTOM DESIGN
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #F4F7F5;
}

[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #E4EBE6;
}

[data-testid="stMetric"] {
    background: white;
    padding: 20px;
    border-radius: 14px;
    border: 1px solid #E5ECE7;
    box-shadow: 0 4px 14px rgba(20,60,40,.04);
    transition: all .25s ease;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 22px rgba(0,120,52,.12);
}

[data-testid="stMetricLabel"] {
    color: #718078;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #17452F;
    font-weight: 800;
}

.hero {
    background: linear-gradient(115deg, #075B32, #007834 65%, #26965A);
    padding: 34px;
    border-radius: 20px;
    color: white;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 28px rgba(0,120,52,.16);
}

.hero:after {
    content: "";
    position: absolute;
    width: 260px;
    height: 260px;
    border: 1px solid rgba(255,255,255,.16);
    border-radius: 50%;
    right: -65px;
    top: -110px;
    box-shadow: 0 0 0 35px rgba(255,255,255,.035),
                0 0 0 70px rgba(255,255,255,.025);
}

.hero h1 {
    color: white;
    font-size: 30px;
    font-weight: 800;
    margin: 0;
}

.hero p {
    color: #E3F3E9;
    margin: 8px 0 0 0;
}

.section-title {
    color: #17452F;
    font-size: 19px;
    font-weight: 750;
    margin: 22px 0 12px 0;
}

.info-card {
    background: white;
    border: 1px solid #E5ECE7;
    border-radius: 14px;
    padding: 18px;
    min-height: 115px;
}

.status-pill {
    display: inline-block;
    border-radius: 30px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 700;
    background: #E7F4EC;
    color: #08743A;
}

.stButton button {
    border-radius: 9px;
    font-weight: 600;
    transition: all .2s ease;
}

.stButton button:hover {
    border-color: #007834;
    transform: translateY(-2px);
}

div[data-testid="stTabs"] button {
    font-weight: 650;
}

footer {
    visibility: hidden;
}

#MainMenu {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def read_csv(upload):
    if upload is None:
        return None
    try:
        return pd.read_csv(upload)
    except Exception:
        try:
            upload.seek(0)
            return pd.read_csv(upload, encoding="latin1")
        except Exception:
            return None


def duration_to_hours(value):
    try:
        return pd.to_timedelta(str(value)).total_seconds() / 3600
    except Exception:
        return 0


def prepare_detail(df):
    df = df.copy()

    if "Percent Completed" in df.columns:
        df["Progress"] = (
            df["Percent Completed"]
            .astype(str)
            .str.replace("%", "", regex=False)
        )
        df["Progress"] = pd.to_numeric(
            df["Progress"], errors="coerce"
        ).fillna(0).clip(0, 100)
    else:
        df["Progress"] = 0

    if "Content Type" in df.columns:
        df = df[
            df["Content Type"].astype(str).str.lower() == "course"
        ].copy()

    df["Status"] = "Not Started"
    df.loc[df["Progress"] > 0, "Status"] = "In Progress"
    df.loc[df["Progress"] >= 100, "Status"] = "Completed"

    return df


def metric_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:

    st.markdown(
        f"""
        <div style="text-align:center;padding:12px 0 22px;">
            <div style="font-size:25px;font-weight:850;color:{GREEN};">
                AL BAWANI
            </div>
            <div style="font-size:11px;letter-spacing:2px;color:#84928A;">
                LEARNING HUB
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("### Data Center")

    summary_file = st.file_uploader(
        "Learner Summary",
        type=["csv"],
        key="summary"
    )

    detail_file = st.file_uploader(
        "Learner Detail",
        type=["csv"],
        key="detail"
    )

    group_file = st.file_uploader(
        "Group Summary (Optional)",
        type=["csv"],
        key="group"
    )

    recommendation_file = st.file_uploader(
        "Recommendation Summary (Optional)",
        type=["csv"],
        key="recommendations"
    )

    st.markdown("---")
    st.markdown("### Brand Identity")

    logo_file = st.file_uploader(
        "Upload Al Bawani Logo",
        type=["png", "jpg", "jpeg"],
        key="logo"
    )

    st.markdown("---")
    st.markdown("### Mandatory Courses")

    mandatory_courses = []

    for i in range(1, 4):
        course = st.text_input(
            f"Mandatory Course {i}",
            placeholder="Enter official course title",
            key=f"mandatory_{i}"
        )
        mandatory_courses.append(course.strip())

    st.markdown("---")
    st.caption("Al Bawani | Learning & Development")


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
summary = read_csv(summary_file)
detail = read_csv(detail_file)
group = read_csv(group_file)
recommendations = read_csv(recommendation_file)

# --------------------------------------------------
# HEADER
# --------------------------------------------------
left, right = st.columns([1, 5])

with left:
    if logo_file:
        st.image(logo_file, width=125)
    else:
        st.markdown(
            f"<h2 style='color:{GREEN};margin-top:12px;'>AL BAWANI</h2>",
            unsafe_allow_html=True
        )

with right:
    st.markdown(
        """
        <div style="padding-top:8px;">
            <div style="font-size:12px;color:#7C8981;
            letter-spacing:2px;font-weight:700;">
                PEOPLE DEVELOPMENT
            </div>
            <div style="font-size:25px;font-weight:800;color:#17452F;">
                Learning & Development Dashboard
            </div>
            <div style="color:#829087;font-size:13px;">
                Employee learning performance and course tracking
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <h1>Build Skills. Grow Together.</h1>
        <p>
        Monitor employee learning journeys, mandatory training
        and professional development in one place.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# EMPTY STATE
# --------------------------------------------------
if summary is None or detail is None:

    st.markdown("### Welcome to Learning Hub")

    st.info(
        "Upload the Learner Summary and Learner Detail CSV reports "
        "using the Data Center in the sidebar to activate analytics."
    )

    c1, c2, c3 = st.columns(3)

    c1.markdown(
        '<div class="info-card"><h3>01</h3>'
        '<b>Employee Insights</b><p>Track learning activity.</p></div>',
        unsafe_allow_html=True
    )

    c2.markdown(
        '<div class="info-card"><h3>02</h3>'
        '<b>Course Progress</b><p>Monitor course completion.</p></div>',
        unsafe_allow_html=True
    )

    c3.markdown(
        '<div class="info-card"><h3>03</h3>'
        '<b>Performance</b><p>Review learning outcomes.</p></div>',
        unsafe_allow_html=True
    )

    st.stop()


# --------------------------------------------------
# DATA PREPARATION
# --------------------------------------------------
summary = summary.copy()
detail = prepare_detail(detail)

if "Hours Viewed" in summary.columns:
    summary["Learning Hours"] = (
        summary["Hours Viewed"].apply(duration_to_hours)
    )
else:
    summary["Learning Hours"] = 0

for col in [
    "Course Views",
    "Course Completions",
    "Days Logged In"
]:
    if col not in summary.columns:
        summary[col] = 0
    summary[col] = pd.to_numeric(
        summary[col], errors="coerce"
    ).fillna(0)

if "department" not in summary.columns:
    summary["department"] = "Not Specified"

if "Name" not in summary.columns:
    summary["Name"] = "Unknown"

if "Email" not in summary.columns:
    summary["Email"] = summary["Name"]

if "Content Name" not in detail.columns:
    detail["Content Name"] = "Unknown Course"

if "Email" not in detail.columns:
    detail["Email"] = ""

if "Name" not in detail.columns:
    detail["Name"] = "Unknown"

# --------------------------------------------------
# FILTERS
# --------------------------------------------------
st.markdown('<div class="section-title">Learning Overview</div>',
            unsafe_allow_html=True)

f1, f2 = st.columns([1, 1])

departments = sorted(
    summary["department"].dropna().astype(str).unique().tolist()
)

with f1:
    selected_department = st.selectbox(
        "Department",
        ["All Departments"] + departments
    )

with f2:
    search_name = st.text_input(
        "Search Employee",
        placeholder="Enter employee name or email"
    )

filtered = summary.copy()

if selected_department != "All Departments":
    filtered = filtered[
        filtered["department"].astype(str) == selected_department
    ]

if search_name:
    filtered = filtered[
        filtered["Name"].astype(str).str.contains(
            search_name, case=False, na=False
        )
        | filtered["Email"].astype(str).str.contains(
            search_name, case=False, na=False
        )
    ]

emails = filtered["Email"].astype(str).tolist()
filtered_detail = detail[
    detail["Email"].astype(str).isin(emails)
].copy()

# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------
total_employees = filtered["Email"].nunique()
total_views = int(filtered["Course Views"].sum())
total_completions = int(filtered["Course Completions"].sum())
total_hours = filtered["Learning Hours"].sum()

k1, k2, k3, k4 = st.columns(4)

with k1:
    metric_card("Total Employees", f"{total_employees:,}")

with k2:
    metric_card("Course Views", f"{total_views:,}")

with k3:
    metric_card("Course Completions", f"{total_completions:,}")

with k4:
    metric_card("Learning Hours", f"{total_hours:,.1f} h")

st.markdown("<br>", unsafe_allow_html=True)

# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Employee Tracking",
    "Course Analytics",
    "Mandatory Program"
])

# --------------------------------------------------
# TAB 1: OVERVIEW
# --------------------------------------------------
with tab1:

    st.markdown("### Learning Performance")

    a, b = st.columns(2)

    with a:
        dept_data = (
            filtered.groupby("department", as_index=False)
            ["Course Completions"].sum()
            .sort_values("Course Completions", ascending=False)
        )

        fig = px.bar(
            dept_data,
            x="department",
            y="Course Completions",
            color_discrete_sequence=[GREEN],
            title="Course Completions by Department"
        )

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=55, b=10),
            xaxis_title="",
            yaxis_title="Completions"
        )

        st.plotly_chart(fig, use_container_width=True)

    with b:
        status_counts = (
            filtered_detail["Status"].value_counts()
            .reindex(
                ["Completed", "In Progress", "Not Started"],
                fill_value=0
            )
            .reset_index()
        )

        status_counts.columns = ["Status", "Count"]

        fig = px.pie(
            status_counts,
            names="Status",
            values="Count",
            hole=0.65,
            color="Status",
            color_discrete_map={
                "Completed": GREEN,
                "In Progress": GOLD,
                "Not Started": "#C9D3CD"
            },
            title="Course Activity Status"
        )

        fig.update_layout(
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=55, b=10),
            legend_title=""
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Department Activity")

    st.dataframe(
        filtered.groupby("department", as_index=False).agg(
            Employees=("Email", "nunique"),
            Course_Views=("Course Views", "sum"),
            Completions=("Course Completions", "sum"),
            Learning_Hours=("Learning Hours", "sum")
        ).round(1),
        use_container_width=True,
        hide_index=True
    )

# --------------------------------------------------
# TAB 2: EMPLOYEE TRACKING
# --------------------------------------------------
with tab2:

    st.markdown("### Employee Directory")

    employee_table = filtered[[
        "Name",
        "Email",
        "department",
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

    employee_options = filtered["Name"].dropna().unique().tolist()

    if employee_options:
        selected_employee = st.selectbox(
            "Select Employee",
            employee_options
        )

        employee_row = filtered[
            filtered["Name"] == selected_employee
        ].iloc[0]

        employee_email = str(employee_row["Email"])

        employee_courses = detail[
            detail["Email"].astype(str) == employee_email
        ].copy()

        p1, p2, p3 = st.columns(3)

        p1.metric("Course Views", int(employee_row["Course Views"]))
        p2.metric(
            "Completions",
            int(employee_row["Course Completions"])
        )
        p3.metric(
            "Learning Hours",
            f"{employee_row['Learning Hours']:.1f} h"
        )

        st.write("**Department:**", employee_row["department"])

        if not employee_courses.empty:
            st.dataframe(
                employee_courses[[
                    "Content Name",
                    "Progress",
                    "Status"
                ]].sort_values("Progress", ascending=False),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No course details found for this employee.")

# --------------------------------------------------
# TAB 3: COURSE ANALYTICS
# --------------------------------------------------
with tab3:

    st.markdown("### Most Viewed Courses")

    if not filtered_detail.empty:

        course_data = (
            filtered_detail.groupby("Content Name", as_index=False)
            .agg(
                Learners=("Email", "nunique"),
                Average_Progress=("Progress", "mean"),
                Completed=("Status", lambda x: (x == "Completed").sum())
            )
            .sort_values("Learners", ascending=False)
            .head(15)
        )

        fig = px.bar(
            course_data.sort_values("Learners"),
            x="Learners",
            y="Content Name",
            orientation="h",
            color="Average_Progress",
            color_continuous_scale=["#DCE9E0", GREEN],
            title="Top 15 Courses by Learners"
        )

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=55, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Course Details")

        st.dataframe(
            course_data.round(1),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No course activity available.")

# --------------------------------------------------
# TAB 4: MANDATORY COURSES
# --------------------------------------------------
with tab4:

    st.markdown("### Mandatory Learning Program")

    configured = [c for c in mandatory_courses if c]

    if not configured:

        st.info(
            "Mandatory course titles have not been configured yet. "
            "Add the official course titles from the sidebar when available."
        )

    else:

        if len(configured) < 3:
            st.warning(
                "Only some mandatory courses are configured. "
                "Add the remaining titles when available."
            )

        mandatory_results = []

        for _, emp in filtered.iterrows():

            emp_email = str(emp["Email"])

            emp_data = detail[
                detail["Email"].astype(str) == emp_email
            ]

            result = {
                "Employee": emp["Name"],
                "Department": emp["department"]
            }

            completed_count = 0

            for i, course_name in enumerate(configured, start=1):

                matches = emp_data[
                    emp_data["Content Name"].astype(str).str.strip().str.casefold()
                    == course_name.casefold()
                ]

                if matches.empty:
                    status = "Not Started"
                    progress = 0
                else:
                    progress = matches["Progress"].max()

                    if progress >= 100:
                        status = "Completed"
                        completed_count += 1
                    elif progress > 0:
                        status = "In Progress"
                    else:
                        status = "Not Started"

                result[f"Course {i}"] = status
                result[f"Progress {i}"] = progress

            result["Completed Mandatory Courses"] = completed_count
            result["Program Progress"] = (
                completed_count / len(configured) * 100
            )

            mandatory_results.append(result)

        mandatory_df = pd.DataFrame(mandatory_results)

        st.markdown("#### Mandatory Course Progress")

        for i, course_name in enumerate(configured, start=1):

            progress_col = f"Progress {i}"
            completed_col = f"Course {i}"

            completed = (
                mandatory_df[completed_col] == "Completed"
            ).sum()

            total = len(mandatory_df)

            st.markdown(f"**{course_name}**")

            st.progress(
                completed / total if total else 0,
                text=f"{completed} of {total} employees completed"
            )

        st.markdown("#### Employee Mandatory Status")

        st.dataframe(
            mandatory_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Mandatory Tracking",
            mandatory_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="mandatory_learning_tracking.csv",
            mime="text/csv"
        )

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("---")

st.markdown(
    """
    <div style="text-align:center;color:#89958E;font-size:12px;padding:10px;">
        AL BAWANI | LEARNING & DEVELOPMENT
        <br>
        Employee Learning Intelligence
    </div>
    """,
    unsafe_allow_html=True
)
