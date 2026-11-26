"""SDSC5003 | Member B: Customer page. No schema changes or writes."""
from pathlib import Path
import sys
import sqlite3
from time import perf_counter

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from modules.customer import customer_module as cm

STATES = ['All', 'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
          'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO',
          'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
ERRORS = (ValueError, OSError, sqlite3.Error, pd.errors.DatabaseError)


def initial_state():
    defaults = {'cust_filters': ('', 'All', '', 20), 'cust_page': 1,
                'cust_snapshot': None, 'cust_selected': None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def move_page(delta):
    st.session_state.cust_page = max(1, st.session_state.cust_page + delta)
    st.session_state.cust_selected = None


def refresh_page():
    st.session_state.cust_snapshot = None


def load_page():
    prefix, state, city, size = st.session_state.cust_filters
    page = st.session_state.cust_page
    key = (prefix, state, city, size, page)
    snapshot = st.session_state.cust_snapshot
    if snapshot is not None and snapshot[0] == key:
        return snapshot[1], snapshot[2]
    start = perf_counter()
    if prefix or state != 'All' or city:
        df = cm.search_customers(prefix=prefix, state=None if state == 'All' else state,
                                 city=city or None, page=page, page_size=size)
    else:
        df = cm.get_customers(page=page, page_size=size)
    elapsed = (perf_counter() - start) * 1000
    # Keep only the current page per session. Refresh re-queries the database.
    st.session_state.cust_snapshot = (key, df, elapsed)
    return df, elapsed


def show_table(df, config):
    st.dataframe(df, hide_index=True, use_container_width=True, column_config=config)


def display(value):
    return 'Not available' if pd.isna(value) else str(value)


def render_details(cid):
    st.divider()
    st.subheader('Customer details')
    details = cm.get_customer_details(cid)
    if details.empty:
        st.warning('This customer is no longer available in the database.')
        return
    d = details.iloc[0]
    summary = cm.get_customer_summary(cid)
    history = cm.get_customer_orders(cid)
    if summary.empty:
        st.warning('No customer summary is available.')
        return
    s = summary.iloc[0]
    st.code(cid, language=None)
    cols = st.columns(4)
    cols[0].metric('Total orders', int(s.total_orders))
    cols[1].metric('Delivered orders', int(s.delivered_orders))
    cols[2].metric('Delivered spend (BRL)', f'R$ {float(s.delivered_spend):,.2f}')
    cols[3].metric('Delivered orders missing payment', int(s.delivered_orders_missing_payment))
    st.caption('Delivered spend is recorded payment for delivered orders only; it is not net revenue.')
    if int(s.delivered_orders_missing_payment):
        st.warning('Some delivered orders have no recorded payment; spending coverage is incomplete.')
    left, right = st.columns(2)
    with left:
        st.markdown('**Latest order location**')
        st.write(f'{display(d.city)}, {display(d.state)}')
        st.write(f'ZIP prefix: {display(d.zip_code_prefix)}')
        st.caption('Historical order location, not a verified current address.')
    with right:
        st.markdown('**Purchase dates**')
        st.write(f'First order: {display(d.first_order_date)}')
        st.write(f'Latest order: {display(d.latest_order_date)}')
    st.subheader('Order history')
    if history.empty:
        st.info('No historical orders are associated with this customer.')
        return
    st.caption(f'{len(history)} order(s), all statuses, newest first. Blank payment means no recorded amount.')
    show_table(history, {
        'order_id': 'Order ID', 'order_purchase_timestamp': 'Purchase date',
        'order_status': 'Status', 'city': 'City', 'state': 'State',
        'order_estimated_delivery_date': 'Estimated delivery',
        'order_delivered_customer_date': 'Actual delivery',
        'payment_amount': st.column_config.NumberColumn('Payment (BRL)', format='R$ %.2f'),
    })
    st.subheader('Order item details')
    # Selecting from this customer's history prevents unrelated order access.
    labels = {r.order_id: f'{r.order_id} | {r.order_status} | {r.order_purchase_timestamp}'
              for r in history.itertuples(index=False)}
    oid = st.selectbox('Select an order', options=list(labels), index=None,
                       format_func=labels.get, key=f'cust_order_{cid}')
    if oid is not None:
        items = cm.get_order_items(cid, oid)
        if items.empty:
            st.info('No product items are recorded for this order.')
        else:
            show_table(items, {
                'order_item_id': 'Item #', 'product_id': 'Product ID', 'seller_id': 'Seller ID',
                'product_category_name': 'Category (original)',
                'product_category_name_english': 'Category (English)',
                'price': st.column_config.NumberColumn('Price (BRL)', format='R$ %.2f'),
                'freight_value': st.column_config.NumberColumn('Freight (BRL)', format='R$ %.2f'),
                'item_total': st.column_config.NumberColumn('Item total (BRL)', format='R$ %.2f'),
            })
            st.caption('Item total is price plus freight; it is not necessarily equal to order payment.')


def render_customer():
    initial_state()
    st.title('Customer Management')
    st.caption('Browse unique customers, search by ID or location, and inspect historical orders.')
    if not cm.DB_PATH.is_file() or not cm.SQL_PATH.is_file():
        st.error('Missing database/olist.db or modules/customer/customer_module.sql. See README.md.')
        return
    prefix, state, city, size = st.session_state.cust_filters
    with st.form('cust_search_form'):
        a, b, c, d = st.columns([3, 1, 2, 1])
        prefix_in = a.text_input('Customer ID / prefix', value=prefix, max_chars=32)
        state_in = b.selectbox('State', STATES, index=STATES.index(state))
        city_in = c.text_input('City (exact)', value=city)
        size_in = d.selectbox('Rows per page', [10, 20, 50, 100], index=[10,20,50,100].index(size))
        submitted = st.form_submit_button('Search', type='primary')
    if submitted:
        st.session_state.cust_filters = (prefix_in.strip(), state_in, city_in.strip(), size_in)
        st.session_state.cust_page = 1
        st.session_state.cust_selected = None
        st.session_state.cust_snapshot = None
    st.caption('Region filters refer to the latest order location. Search runs only when submitted.')
    try:
        df, elapsed = load_page()
    except ERRORS as exc:
        st.error(f'Customer query failed: {exc}')
        return
    page = st.session_state.cust_page
    size = st.session_state.cust_filters[3]
    st.subheader('Customer list')
    st.caption(f'Page {page} | {len(df)} row(s) | Last page fetch: {elapsed:.2f} ms (Python + SQLite, not browser rendering).')
    if df.empty:
        st.info('No customers on this page. Change the filters or return to the previous page.')
    else:
        show_table(df, {'customer_unique_id': 'Customer unique ID', 'city': 'Latest city',
                        'state': 'State', 'total_orders': 'Total orders'})
    a, b, c = st.columns(3)
    a.button('Previous', disabled=page == 1, on_click=move_page, args=(-1,), key='cust_previous')
    b.button('Next', disabled=len(df) < size, on_click=move_page, args=(1,), key='cust_next')
    c.button('Refresh page', on_click=refresh_page, key='cust_refresh')
    if not df.empty:
        with st.form('cust_select_form'):
            selected = st.selectbox('Select customer', df.customer_unique_id.tolist(), index=None)
            opened = st.form_submit_button('View customer')
        if opened:
            if selected is None:
                st.warning('Select a customer first.')
            else:
                st.session_state.cust_selected = selected
    if st.session_state.cust_selected is not None:
        try:
            render_details(st.session_state.cust_selected)
        except ERRORS as exc:
            st.error(f'Customer details could not be loaded: {exc}')


render_customer()
