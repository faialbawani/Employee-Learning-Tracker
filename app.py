import io
import json
from pathlib import Path
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Al Bawani | Learning Hub", page_icon="📚", layout="wide")

GREEN = "#08783E"
DARK = "#075B32"
GOLD = "#C6A45B"
MUTED = "#718078"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family: Inter, sans-serif;}
.stApp {background:#F5F8F6;color:#20352A;}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid #E3EBE5;}
[data-testid="stMetric"] {background:#fff;padding:16px;border:1px solid #E3EBE5;border-radius:14px;box-shadow:0 3px 12px rgba(20,60,40,.04);}
[data-testid="stMetricLabel"] {color:#718078;font-weight:600;}
[data-testid="stMetricValue"] {color:#075B32;font-weight:800;}
.employee-name {font-size:34px!important;font-weight:800!important;color:#075B32!important;line-height:1.2;margin:4px 0 8px;}
.small-note {color:#718078;font-size:12px;}
.section-head {font-size:20px;font-weight:750;color:#17452F;margin:14px 0 8px;}
div[data-testid="stTabs"] button {font-weight:650;}
.stButton button,.stDownloadButton button {border-radius:9px;font-weight:650;}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def read_csv_upload(upload):
    if upload is None:
        return None
    raw = upload.getvalue()
    if not raw:
        return pd.DataFrame()
    try:
        return pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(raw), encoding="latin1")

def txt(s):
    return s.fillna("").astype(str).str.strip()

def find_col(df, candidates):
    if df is None:
        return None
    lookup = {str(c).strip().casefold(): c for c in df.columns}
    for candidate in candidates:
        if candidate.casefold() in lookup:
            return lookup[candidate.casefold()]
    return None

def to_num(series, default=0):
    return pd.to_numeric(series, errors="coerce").fillna(default)

def hours_to_float(value):
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    s = str(value).strip()
    try:
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = map(float, parts)
            return h + m/60 + sec/3600
        if len(parts) == 2:
            m, sec = map(float, parts)
            return m/60 + sec/3600
        return float(s)
    except Exception:
        return 0.0

def progress_values(series):
    return pd.to_numeric(
        series.fillna("").astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce"
    ).clip(0, 100)

def status_from_progress(p):
    if pd.isna(p):
        return "Unknown"
    if p >= 100:
        return "Completed"
    if p > 0:
        return "In Progress"
    return "Not Started"

def normalized_email(s):
    return txt(s).str.lower()

def safe_date_col(df, candidates):
    c = find_col(df, candidates)
    if c:
        return pd.to_datetime(df[c], errors="coerce")
    return pd.Series(pd.NaT, index=df.index)

def prepare_management(raw):
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    email = find_col(df, ["Email"])
    name = find_col(df, ["Name"])
    if not email or not name:
        raise ValueError("Learner Management must contain Name and Email columns.")
    df["Email Key"] = normalized_email(df[email])
    df["Employee Name"] = txt(df[name])
    dept = find_col(df, ["department", "Department"])
    df["Department"] = txt(df[dept]).replace("", "Not Specified") if dept else "Not Specified"
    title = find_col(df, ["Business Title"])
    df["Business Title"] = txt(df[title]) if title else ""
    uid = find_col(df, ["Unique User ID"])
    df["Unique User ID"] = txt(df[uid]) if uid else ""
    last_login = find_col(df, ["Last Login During Selected Time Range (PST/PDT)", "Last Login"])
    df["Login Data Available"] = last_login is not None
    df["Last Login"] = pd.to_datetime(df[last_login], errors="coerce") if last_login else pd.NaT
    days = find_col(df, ["Days Logged In"])
    df["Days Logged In"] = to_num(df[days]) if days else 0
    hours = find_col(df, ["Hours Viewed"])
    df["Learning Hours"] = df[hours].apply(hours_to_float) if hours else 0.0
    license_col = find_col(df, ["License Status"])
    df["License Status"] = txt(df[license_col]) if license_col else "Unknown"
    df = df[df["Email Key"] != ""].drop_duplicates("Email Key", keep="last")
    df["Login Status"] = df["Last Login"].notna().map({True:"Logged In", False:"No Login During Selected Period"})
    return df

def prepare_summary(raw):
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    email, name = find_col(df, ["Email"]), find_col(df, ["Name"])
    if not email or not name:
        raise ValueError("Learner Summary must contain Name and Email columns.")
    df["Email Key"] = normalized_email(df[email])
    df["Employee Name"] = txt(df[name])
    dept = find_col(df, ["department", "Department"])
    df["Department"] = txt(df[dept]).replace("", "Not Specified") if dept else "Not Specified"
    for label, candidates in {
        "Days Logged In":["Days Logged In"],
        "Course Views":["Course Views"],
        "Course Completions":["Course Completions"]
    }.items():
        c = find_col(df, candidates)
        df[label] = to_num(df[c]) if c else 0
    h = find_col(df, ["Hours Viewed"])
    df["Learning Hours"] = df[h].apply(hours_to_float) if h else 0.0
    return df[df["Email Key"] != ""].drop_duplicates("Email Key", keep="last")

def prepare_detail(raw):
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    email, name, content = find_col(df, ["Email"]), find_col(df, ["Name"]), find_col(df, ["Content Name"])
    if not email or not name or not content:
        raise ValueError("Learner Detail must contain Name, Email and Content Name.")
    df["Email Key"] = normalized_email(df[email])
    df["Employee Name"] = txt(df[name])
    df["Course Name"] = txt(df[content])
    type_col = find_col(df, ["Content Type"])
    df["Content Type"] = txt(df[type_col]) if type_col else "Unknown"
    pct = find_col(df, ["Percent Completed"])
    df["Progress"] = progress_values(df[pct]) if pct else pd.Series(float("nan"), index=df.index)
    df["Status"] = df["Progress"].apply(status_from_progress)
    cid = find_col(df, ["Content ID"])
    df["Course ID"] = txt(df[cid]) if cid else ""
    df["Course Key"] = df["Course ID"].where(df["Course ID"] != "", df["Course Name"].str.casefold())
    hrs = find_col(df, ["Hours Viewed (LinkedIn Learning and Organization Content Only)", "Hours Viewed"])
    df["Learning Hours"] = df[hrs].apply(hours_to_float) if hrs else 0.0
    for label, candidates in {
        "Started Date":["Started (PST/PDT)", "Started"],
        "Last Viewed":["Last Viewed During Time Range (PST/PDT)", "Last Viewed"],
        "Completed Date":["Completed At (PST/PDT)", "Completed At"]
    }.items():
        c = find_col(df, candidates)
        df[label] = pd.to_datetime(df[c], errors="coerce") if c else pd.NaT
    # Retain only actual course rows for course reporting; other content is preserved in raw activity separately.
    return df[df["Email Key"] != ""].copy()

def fmt_hours(v):
    return f"{float(v):,.1f} h"

def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

# ---------- Sidebar / inputs ----------
with st.sidebar:
    logo = Path("AL-Bawani-logo.png")
    if logo.exists():
        st.image(str(logo), width=175)
    st.markdown("## Learning Hub")
    st.caption("AL BAWANI | PEOPLE DEVELOPMENT")
    st.divider()
    st.markdown("### Upload LinkedIn Learning Reports")
    management_file = st.file_uploader("Learner Management", type=["csv"], key="management")
    summary_file = st.file_uploader("Learner Summary", type=["csv"], key="summary")
    detail_file = st.file_uploader("Learner Detail", type=["csv"], key="detail")
    group_file = st.file_uploader("Group Summary (optional)", type=["csv"], key="group")
    content_file = st.file_uploader("Content Summary (optional)", type=["csv"], key="content")
    rec_summary_file = st.file_uploader("Recommendation Summary (optional)", type=["csv"], key="recsummary")
    rec_detail_file = st.file_uploader("Recommendation Detail (optional)", type=["csv"], key="recdetail")
    st.divider()
    report_period = st.text_input("Reporting Period", "17 Oct – 16 Nov 2026")
    st.caption("Login status is based on the selected reporting period.")
    st.divider()
    st.markdown("### Department Mandatory Course Setup")
    config_upload = st.file_uploader("Upload saved mandatory-course configuration (JSON)", type=["json"], key="mandatory_config")
    config = {}
    if config_upload:
        try:
            config = json.loads(config_upload.getvalue().decode("utf-8"))
        except Exception:
            st.error("The mandatory-course configuration file is invalid.")
    st.caption("Configure three required courses separately for each department. Download the JSON to preserve your setup.")
    archive_file = st.file_uploader("Previous Monthly History (CSV, optional)", type=["csv"], key="archive")

# ---------- Header ----------
left, right = st.columns([1, 5], vertical_alignment="center")
with left:
    if Path("AL-Bawani-logo.png").exists():
        st.image("AL-Bawani-logo.png", width=170)
    else:
        st.markdown(f"<h2 style='color:{GREEN}'>AL BAWANI</h2>", unsafe_allow_html=True)
with right:
    st.markdown("<div style='font-size:11px;letter-spacing:2px;color:#718078;font-weight:800'>PEOPLE DEVELOPMENT</div><div style='font-size:28px;font-weight:800;color:#17452F'>Learning &amp; Development Dashboard</div><div style='color:#718078'>Employee access, course progress and mandatory learning</div>", unsafe_allow_html=True)

# ---------- Load ----------
try:
    management_raw = read_csv_upload(management_file)
    summary_raw = read_csv_upload(summary_file)
    detail_raw = read_csv_upload(detail_file)
    group_df = read_csv_upload(group_file)
    content_df = read_csv_upload(content_file)
    rec_summary_df = read_csv_upload(rec_summary_file)
    rec_detail_df = read_csv_upload(rec_detail_file)
    management = prepare_management(management_raw)
    summary = prepare_summary(summary_raw)
    detail_all = prepare_detail(detail_raw)
except Exception as e:
    st.error(f"Unable to process the uploaded reports: {e}")
    st.stop()

if management.empty or detail_all.empty:
    st.info("Upload Learner Management and Learner Detail to activate access tracking and employee course profiles. Learner Summary is also recommended for employee-level totals.")
    st.stop()

# Employee master = management population. Merge summary metrics, retaining everyone in management.
master = management.copy()
if not summary.empty:
    sm = summary[["Email Key","Course Views","Course Completions","Learning Hours","Days Logged In"]].copy()
    sm = sm.rename(columns={"Learning Hours":"Summary Learning Hours","Days Logged In":"Summary Days Logged In"})
    master = master.merge(sm, on="Email Key", how="left")
else:
    for c in ["Course Views","Course Completions","Summary Learning Hours","Summary Days Logged In"]:
        master[c] = pd.NA

master["Course Views"] = pd.to_numeric(master["Course Views"], errors="coerce")
master["Course Completions"] = pd.to_numeric(master["Course Completions"], errors="coerce")
master["Has Course Activity"] = master["Email Key"].isin(set(detail_all.loc[detail_all["Content Type"].str.casefold()=="course","Email Key"]))
master["Course Activity Status"] = master["Has Course Activity"].map({True:"Course Activity",False:"No Course Activity"})
master["Login Status"] = master.apply(
    lambda r: "Login Data Not Available" if not bool(r["Login Data Available"])
    else ("No Login During Selected Period" if pd.isna(r["Last Login"]) else "Logged In"),
    axis=1
)

# Restrict detailed course views to actual course content, but keep all content types available in activity totals.
courses = detail_all[detail_all["Content Type"].str.casefold()=="course"].copy()
if not courses.empty:
    courses = courses.sort_values(["Progress","Last Viewed"], ascending=[False,False], na_position="last")
    courses = courses.drop_duplicates(["Email Key","Course Key"], keep="first")

departments = sorted(master["Department"].fillna("Not Specified").unique().tolist())
for dept in departments:
    config.setdefault(dept, ["","",""])
    if not isinstance(config[dept], list):
        config[dept] = ["","",""]
    config[dept] = (config[dept] + ["","",""])[:3]

# ---------- Global filters ----------
f1, f2, f3 = st.columns([1.2,1.2,1.6])
with f1:
    dept_filter = st.selectbox("Department", ["All Departments"] + departments)
with f2:
    login_filter = st.selectbox("Login Status", ["All","Logged In","No Login During Selected Period","Login Data Not Available"])
with f3:
    employee_search = st.text_input("Search employee by name or email", placeholder="Type a name or email")

filtered = master.copy()
if dept_filter != "All Departments":
    filtered = filtered[filtered["Department"]==dept_filter]
if login_filter != "All":
    filtered = filtered[filtered["Login Status"]==login_filter]
if employee_search:
    filtered = filtered[
        filtered["Employee Name"].str.contains(employee_search, case=False, na=False) |
        filtered["Email Key"].str.contains(employee_search, case=False, na=False)
    ]
filtered_emails = set(filtered["Email Key"])
filtered_courses = courses[courses["Email Key"].isin(filtered_emails)].copy()

# ---------- Notice ----------
with st.expander("Employee Access Status – Important Note", expanded=False):
    st.markdown("""
**Login activity and course activity are tracked separately.**

- **No Login During Selected Period:** No login was recorded during the selected reporting period. This does not necessarily mean the employee has never accessed the platform.
- **No Course Activity:** No course activity appears in the available learning report. The employee may still have logged in.
- **Login Data Not Available:** Login information is missing or unavailable to verify the employee's access status.
""")

# ---------- Tabs ----------
overview_tab, access_tab, profiles_tab, mandatory_tab, analytics_tab, history_tab = st.tabs([
    "Overview","Employee Access","Employee Profiles","Mandatory Program","Course Analytics","Monthly History"
])

with overview_tab:
    st.markdown("### Learning & Access Overview")
    total = len(filtered)
    logged = int((filtered["Login Status"]=="Logged In").sum())
    no_login = int((filtered["Login Status"]=="No Login During Selected Period").sum())
    login_na = int((filtered["Login Status"]=="Login Data Not Available").sum())
    with_activity = int(filtered["Has Course Activity"].sum())
    no_activity = total-with_activity
    comp = int(filtered["Course Completions"].fillna(0).sum()) if filtered["Course Completions"].notna().any() else int((filtered_courses["Status"]=="Completed").sum())
    hrs = float(filtered["Learning Hours"].sum())
    k = st.columns(4)
    k[0].metric("Licensed Employees", f"{total:,}")
    k[1].metric("Logged In", f"{logged:,}")
    k[2].metric("No Login in Period", f"{no_login:,}")
    k[3].metric("Login Data Unavailable", f"{login_na:,}")
    k2 = st.columns(4)
    k2[0].metric("With Course Activity", f"{with_activity:,}")
    k2[1].metric("No Course Activity", f"{no_activity:,}")
    k2[2].metric("Course Completions", f"{comp:,}")
    k2[3].metric("Learning Hours", fmt_hours(hrs))
    st.info("Login activity and course activity are different measures. Employees with no course activity may still have logged in.")
    c1,c2 = st.columns(2)
    with c1:
        by_login = filtered.groupby(["Department","Login Status"], as_index=False).size()
        if not by_login.empty:
            fig=px.bar(by_login,x="Department",y="size",color="Login Status",barmode="stack",title="Login Status by Department",color_discrete_map={"Logged In":GREEN,"No Login During Selected Period":GOLD,"Login Data Not Available":"#AAB5AE"})
            fig.update_layout(paper_bgcolor="white",plot_bgcolor="white",xaxis_title="",yaxis_title="Employees",legend_title="")
            st.plotly_chart(fig,use_container_width=True)
    with c2:
        by_activity=filtered.groupby(["Department","Course Activity Status"],as_index=False).size()
        if not by_activity.empty:
            fig=px.bar(by_activity,x="Department",y="size",color="Course Activity Status",barmode="stack",title="Course Activity by Department",color_discrete_map={"Course Activity":GREEN,"No Course Activity":GOLD})
            fig.update_layout(paper_bgcolor="white",plot_bgcolor="white",xaxis_title="",yaxis_title="Employees",legend_title="")
            st.plotly_chart(fig,use_container_width=True)
    dept_table=filtered.groupby("Department",as_index=False).agg(Employees=("Email Key","nunique"),Logged_In=("Login Status",lambda s:(s=="Logged In").sum()),No_Login=("Login Status",lambda s:(s=="No Login During Selected Period").sum()),No_Course_Activity=("Has Course Activity",lambda s:(~s).sum()),Learning_Hours=("Learning Hours","sum"))
    st.markdown("### Department Summary")
    st.dataframe(dept_table.round(1),use_container_width=True,hide_index=True)

with access_tab:
    st.markdown("### Employee Access Tracking")
    access_cols=["Employee Name","Department","Business Title","Email Key","Login Status","Last Login","Days Logged In","Learning Hours","Course Activity Status","License Status"]
    access_view=filtered[access_cols].copy()
    access_view["Last Login"]=access_view["Last Login"].dt.strftime("%d %b %Y %H:%M").fillna("Not Available")
    access_view["Learning Hours"]=access_view["Learning Hours"].round(2)
    st.dataframe(access_view,use_container_width=True,hide_index=True)
    st.download_button("Download Employee Access Report",csv_bytes(access_view),file_name="employee_access_report.csv",mime="text/csv")

with profiles_tab:
    st.markdown("### Employee Profiles")
    employee_options=filtered.sort_values("Employee Name")["Email Key"].tolist()
    if employee_options:
        labels={r["Email Key"]:f'{r["Employee Name"]} — {r["Department"]}' for _,r in filtered.iterrows()}
        selected_email=st.selectbox("Select employee",employee_options,format_func=lambda x:labels.get(x,x))
        emp=master[master["Email Key"]==selected_email].iloc[0]
        st.markdown(f'<div class="employee-name">{emp["Employee Name"]}</div>',unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:15px;color:#718078;margin-bottom:16px">{emp["Department"]} &nbsp; | &nbsp; {emp["Business Title"] or "Business title not available"}</div>',unsafe_allow_html=True)
        p1,p2,p3,p4=st.columns(4)
        p1.metric("Login Status",emp["Login Status"])
        p2.metric("Days Logged In",int(emp["Days Logged In"]))
        p3.metric("Learning Hours",fmt_hours(emp["Learning Hours"]))
        p4.metric("Course Completions",int(emp["Course Completions"]) if pd.notna(emp["Course Completions"]) else int((courses.loc[courses["Email Key"]==selected_email,"Status"]=="Completed").sum()))
        st.caption(f'{emp["Email Key"]}  |  User ID: {emp["Unique User ID"] or "Not available"}  |  Last login: {emp["Last Login"].strftime("%d %b %Y %H:%M") if pd.notna(emp["Last Login"]) else "Not available"}')
        st.divider()
        st.markdown("#### Mandatory Courses")
        required=config.get(emp["Department"],["","",""])
        required=[x.strip() for x in required if str(x).strip()]
        if len(required)!=3:
            st.warning("Mandatory Courses Not Configured — configure all three required courses for this department in the Mandatory Program tab.")
        else:
            ec=courses[courses["Email Key"]==selected_email]
            rows=[]
            for title in required:
                match=ec[ec["Course Name"].str.casefold()==title.casefold()]
                progress=match["Progress"].max() if not match.empty else 0
                status=status_from_progress(progress)
                rows.append({"Required Course":title,"Progress":f"{progress:.0f}%" if pd.notna(progress) else "Unknown","Status":status})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            done=sum(x["Status"]=="Completed" for x in rows)
            st.progress(done/3,text=f"{done} of 3 mandatory courses completed")
        st.markdown("#### All Courses")
        emp_courses=courses[courses["Email Key"]==selected_email].copy()
        if emp_courses.empty:
            st.info("No course activity appears in the available Learner Detail report. This does not confirm that the employee has never logged in.")
        else:
            cols=["Course Name","Content Type","Progress","Status","Learning Hours","Started Date","Last Viewed","Completed Date"]
            cv=emp_courses[cols].copy()
            cv["Progress"]=cv["Progress"].apply(lambda x:f"{x:.0f}%" if pd.notna(x) else "Unknown")
            for dc in ["Started Date","Last Viewed","Completed Date"]:
                cv[dc]=cv[dc].dt.strftime("%d %b %Y").fillna("—")
            cv["Learning Hours"]=cv["Learning Hours"].round(2)
            st.dataframe(cv,use_container_width=True,hide_index=True)
            st.download_button("Download Employee Course Details",csv_bytes(cv),file_name="employee_course_details.csv",mime="text/csv")

with mandatory_tab:
    st.markdown("### Department Mandatory Course Configuration")
    st.caption("Set exactly three required courses for each department. Course names must match the LinkedIn Learning report, unless an approved course ID mapping is used.")
    selected_config_dept=st.selectbox("Choose department to configure",departments,key="mandatory_department")
    current=config.get(selected_config_dept,["","",""])
    updated=[]
    c1,c2,c3=st.columns(3)
    for idx,col in enumerate([c1,c2,c3]):
        with col:
            updated.append(st.text_input(f"Mandatory Course {idx+1}",value=current[idx],key=f"req_{selected_config_dept}_{idx}"))
    config[selected_config_dept]=updated
    st.download_button("Download Department Course Configuration",json.dumps(config,ensure_ascii=False,indent=2).encode("utf-8"),file_name="mandatory_courses_by_department.json",mime="application/json")
    st.caption("Keep this JSON file and upload it in the sidebar on your next visit. Streamlit Community Cloud does not guarantee persistence for in-app file changes.")
    st.divider()
    if all(x.strip() for x in updated):
        rows=[]
        for _,emp in filtered[filtered["Department"]==selected_config_dept].iterrows():
            ec=courses[courses["Email Key"]==emp["Email Key"]]
            completed=0
            row={"Employee":emp["Employee Name"],"Email":emp["Email Key"]}
            for i,title in enumerate(updated,1):
                m=ec[ec["Course Name"].str.casefold()==title.strip().casefold()]
                p=m["Progress"].max() if not m.empty else 0
                s=status_from_progress(p)
                row[f"Course {i} – {title}"]=s
                completed += (s=="Completed")
            row["Completed Courses"]=completed
            row["Mandatory Progress"]=f"{completed}/3"
            rows.append(row)
        mandatory_df=pd.DataFrame(rows)
        st.markdown("#### Employee Mandatory Completion")
        st.dataframe(mandatory_df,use_container_width=True,hide_index=True)
        done_employees=int((mandatory_df["Completed Courses"]==3).sum()) if not mandatory_df.empty else 0
        st.metric("Employees Completed All Three",f"{done_employees} / {len(mandatory_df)}")
        st.download_button("Download Mandatory Progress",csv_bytes(mandatory_df),file_name="mandatory_progress.csv",mime="text/csv")
    else:
        st.info("Complete all three course names to calculate mandatory completion for this department.")

with analytics_tab:
    st.markdown("### Course Analytics")
    if not filtered_courses.empty:
        ca=filtered_courses.groupby("Course Name",as_index=False).agg(Unique_Learners=("Email Key","nunique"),Completions=("Status",lambda s:(s=="Completed").sum()),In_Progress=("Status",lambda s:(s=="In Progress").sum()),Not_Started=("Status",lambda s:(s=="Not Started").sum()),Average_Progress=("Progress","mean"),Learning_Hours=("Learning Hours","sum"))
        ca=ca.sort_values("Unique_Learners",ascending=False)
        st.dataframe(ca.round(1),use_container_width=True,hide_index=True)
        top=ca.head(12).sort_values("Unique_Learners")
        fig=px.bar(top,x="Unique_Learners",y="Course Name",orientation="h",color="Average_Progress",color_continuous_scale=["#DCE9E0",GREEN],title="Most Viewed Courses")
        fig.update_layout(paper_bgcolor="white",plot_bgcolor="white",xaxis_title="Unique learners",yaxis_title="")
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.info("No course records are available for the selected filters.")
    if content_df is not None and not content_df.empty:
        st.markdown("#### Content Summary")
        st.dataframe(content_df,use_container_width=True,hide_index=True)
    if rec_summary_df is not None and rec_summary_df.empty:
        st.caption("No recommendation records are available in this reporting period.")

with history_tab:
    st.markdown("### Monthly Learning History")
    st.caption("Upload the previous archive, then download the combined archive after each reporting period.")
    current_history=courses.copy()
    current_history["Period"]=report_period
    current_history=current_history[["Period","Email Key","Employee Name","Course Key","Course Name","Progress","Status","Learning Hours"]]
    if archive_file is not None:
        try:
            old=pd.read_csv(archive_file,encoding="utf-8-sig")
        except Exception:
            old=pd.DataFrame()
    else:
        old=pd.DataFrame()
    hist=pd.concat([old,current_history],ignore_index=True,sort=False)
    if not hist.empty:
        if "Period" in hist and "Email Key" in hist:
            hist=hist.drop_duplicates(["Period","Email Key","Course Key"],keep="last")
        st.metric("Historical Course Records",f"{len(hist):,}")
        st.dataframe(hist,use_container_width=True,hide_index=True)
        st.download_button("Download Updated Monthly Archive",csv_bytes(hist),file_name="al_bawani_learning_history.csv",mime="text/csv")
    else:
        st.info("No historical records available yet.")

st.divider()
st.markdown("<div style='text-align:center;color:#89958E;font-size:11px;padding:10px'>AL BAWANI | LEARNING & DEVELOPMENT</div>",unsafe_allow_html=True)
