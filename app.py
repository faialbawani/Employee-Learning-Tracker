
import streamlit as st

st.set_page_config(
    page_title="Employee Learning Tracker",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #F5F8F6;
}
h1, h2, h3 {
    color: #174D3A;
}
[data-testid="stMetric"] {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #E3ECE6;
}
</style>
""", unsafe_allow_html=True)

st.title("Employee Learning Tracker")
st.caption("Learning & Development | Employee Training Overview")

st.divider()

st.subheader("Training Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Employees", "33")
col2.metric("Completed Courses", "105")
col3.metric("Course Views", "285")
col4.metric("Learning Hours", "121")

st.divider()

st.subheader("Mandatory Learning Program")

st.info("Three mandatory courses will be configured once the official course list is received.")

st.subheader("Employee Tracking")

st.write("Employee progress and course completion details will appear here.")

st.caption("Employee Learning Tracker | Version 1.0")
