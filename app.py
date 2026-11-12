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
