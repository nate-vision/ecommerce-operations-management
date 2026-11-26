"""Shared entry point. Only register pages that have been delivered."""
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Olist Operations Management", layout="wide", initial_sidebar_state="expanded")
SPECS = [
    ("pages/01_Seller.py", "Seller", ":material/store:"),
    ("pages/02_Customer.py", "Customer", ":material/group:"),
    ("pages/03_Product.py", "Product", ":material/inventory_2:"),
    ("pages/04_Order.py", "Order", ":material/shopping_cart:"),
    ("pages/05_Payment_Review.py", "Payment & Review", ":material/payments:"),
]
pages = [st.Page(path, title=title, icon=icon) for path, title, icon in SPECS if (ROOT / path).is_file()]
if not pages:
    st.info("No modules available yet.")
    st.stop()
st.navigation(pages).run()
