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
