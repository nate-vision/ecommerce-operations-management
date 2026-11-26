"""Standalone Customer launcher. Run from the project root for shared theme."""
from pathlib import Path
import runpy
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

def customer_page():
    runpy.run_path(str(ROOT / "pages" / "02_Customer.py"), run_name="__main__")

st.set_page_config(page_title="Olist | Customer Management", layout="wide")
st.navigation([st.Page(customer_page, title="Customer", icon=":material/group:")]).run()
