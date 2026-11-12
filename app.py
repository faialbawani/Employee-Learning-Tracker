

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
