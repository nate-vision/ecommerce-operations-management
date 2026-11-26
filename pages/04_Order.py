from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.order.order_manager import (  # noqa: E402
    VALID_STATUSES,
    benchmark_order_queries,
    get_order_detail,
    get_status_summary,
    search_orders,
    track_order_status,
    update_order_status,
)


def _format_currency(value: Any) -> str:
    try:
        return f"R$ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "R$ 0.00"


def _render_overview_metrics(summary_rows: List[Dict[str, Any]]) -> None:
    total_orders = sum(int(r.get("order_count") or 0) for r in summary_rows)
    total_gmv = sum(float(r.get("total_gmv") or 0.0) for r in summary_rows)
    delivered_row = next((r for r in summary_rows if r.get("order_status") == "delivered"), None)
    delivered_count = int(delivered_row.get("order_count") or 0) if delivered_row else 0
    delivered_share = float(delivered_row.get("share_pct") or 0.0) if delivered_row else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Orders", f"{total_orders:,}")
    c2.metric("Total GMV", _format_currency(total_gmv))
    c3.metric("Delivered Orders", f"{delivered_count:,}")
    c4.metric("Delivered Share", f"{delivered_share:.2f}%")

    if summary_rows:
        with st.expander("Order Status Breakdown", expanded=False):
            st.dataframe(summary_rows, use_container_width=True, hide_index=True)


def _render_order_search_tab() -> None:
    st.subheader("Order Search & Pagination")

    with st.form("order_search_form"):
        col1, col2, col3 = st.columns(3)
        order_id_input = col1.text_input("Order ID (Prefix or Exact)", placeholder="e.g. 0008288a...")
        customer_id_input = col2.text_input("Customer ID", placeholder="Exact customer_id")
        customer_unique_input = col3.text_input(
            "Customer Unique ID", placeholder="Exact customer_unique_id"
        )

        col4, col5, col6 = st.columns(3)
        status_options = ["All"] + list(VALID_STATUSES)
        selected_status = col4.selectbox("Order Status", status_options, index=0)
        start_date_input = col5.text_input(
            "Start Date (YYYY-MM-DD)", placeholder="2018-01-01 00:00:00"
        )
        end_date_input = col6.text_input(
            "End Date (YYYY-MM-DD)", placeholder="2018-12-31 23:59:59"
        )

        col7, col8, col9 = st.columns([1, 1, 2])
        page_size = col7.selectbox("Page Size", [10, 20, 50, 100], index=1)
        page_number = col8.number_input("Page", min_value=1, value=1, step=1)
        submitted = col9.form_submit_button("Search Orders", use_container_width=True)

    offset = (int(page_number) - 1) * int(page_size)
    status_filter: Optional[str] = None if selected_status == "All" else selected_status

    if submitted or "order_search_loaded" not in st.session_state:
        st.session_state["order_search_loaded"] = True
        st.session_state["order_search_params"] = {
            "order_id": order_id_input.strip() or None,
            "customer_id": customer_id_input.strip() or None,
            "customer_unique_id": customer_unique_input.strip() or None,
            "status": status_filter,
            "start_date": start_date_input.strip() or None,
            "end_date": end_date_input.strip() or None,
            "limit": int(page_size),
            "offset": offset,
        }

    params = st.session_state.get("order_search_params", {})
    try:
        rows = search_orders(**params)
    except Exception as exc:
        st.error(f"Failed to search orders: {exc}")
        return

    st.caption(f"Showing up to {params.get('limit', 20)} rows | Page {int(page_number)} (offset {offset})")
    if not rows:
        st.info("No orders matched the current filter criteria.")
        return

    st.dataframe(rows, use_container_width=True, hide_index=True)

    matched_ids = [r["order_id"] for r in rows if r.get("order_id")]
    if matched_ids:
        selected_id = st.selectbox("Quick Select Order ID for Inspection", matched_ids)
        if st.button("Load Selected Order in Detail & Tracking"):
            st.session_state["inspected_order_id"] = selected_id
            st.info(f"Selected Order ID: {selected_id}. Switch to 'Order Detail & SLA' or 'Status Update'.")


def _render_detail_and_tracking_tab(default_order_id: str) -> None:
    st.subheader("Order Detail & Lifecycle SLA")

    order_id = st.text_input(
        "Order ID",
        value=default_order_id,
        key="detail_order_id_input",
        placeholder="Enter full order_id",
    ).strip()

    if not order_id:
        st.warning("Enter an Order ID to inspect full details and delivery timeline.")
        return

    try:
        detail = get_order_detail(order_id)
        tracking = track_order_status(order_id)
    except Exception as exc:
        st.error(f"Error retrieving order information: {exc}")
        return

    if detail is None or tracking is None:
        st.warning(f"Order '{order_id}' was not found.")
        return

    header: Dict[str, Any] = detail["header"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Status", str(header.get("order_status") or "unknown"))
    m2.metric("SLA Status", str(tracking.get("sla_status") or "N/A"))
    m3.metric("Order Total", _format_currency(header.get("order_total")))
    m4.metric("Total Paid", _format_currency(header.get("total_paid")))

    st.markdown("#### Order Header")
    header_summary = {
        "order_id": header.get("order_id"),
        "customer_id": header.get("customer_id"),
        "customer_unique_id": header.get("customer_unique_id"),
        "customer_location": f"{header.get('customer_city') or 'N/A'}, {header.get('customer_state') or 'N/A'}",
        "items_subtotal": _format_currency(header.get("items_subtotal")),
        "freight_total": _format_currency(header.get("freight_total")),
        "estimated_delivery_date": header.get("order_estimated_delivery_date"),
    }
    st.json(header_summary)

    st.markdown("#### Lifecycle Timeline")
    timeline = tracking.get("timeline") or []
    st.dataframe(timeline, use_container_width=True, hide_index=True)
    allowed_next = tracking.get("next_allowed_statuses") or []
    st.caption(f"Allowed Next Statuses: {', '.join(allowed_next) if allowed_next else 'None (terminal state)'}")

    st.markdown("#### Line Items")
    items = detail.get("items") or []
    if items:
        st.dataframe(items, use_container_width=True, hide_index=True)
    else:
        st.info("No line items found for this order.")

    col_pay, col_rev = st.columns(2)
    with col_pay:
        st.markdown("#### Payments")
        payments = detail.get("payments") or []
        if payments:
            st.dataframe(payments, use_container_width=True, hide_index=True)
        else:
            st.info("No payment records found.")

    with col_rev:
        st.markdown("#### Reviews")
        reviews = detail.get("reviews") or []
        if reviews:
            st.dataframe(reviews, use_container_width=True, hide_index=True)
        else:
            st.info("No review records found.")


def _render_status_update_tab(default_order_id: str) -> None:
    st.subheader("Transactional Order Status Update")
    st.caption(
        "Updates run inside an explicit SQLite transaction with state-machine validation "
        "and automatic rollback on invalid transitions or database errors."
    )

    with st.form("update_order_status_form"):
        order_id = st.text_input("Target Order ID", value=default_order_id)
        new_status = st.selectbox("New Order Status", list(VALID_STATUSES))
        event_timestamp = st.text_input(
            "Event Timestamp (Optional, YYYY-MM-DD HH:MM:SS)",
            placeholder="Leave blank to use current timestamp",
        )
        strict_transition = st.checkbox("Enforce State Machine Transition Rules", value=True)
        submitted = st.form_submit_button("Commit Status Update")

    if submitted:
        if not order_id.strip():
            st.error("Order ID is required.")
            return
        try:
            result = update_order_status(
                order_id=order_id.strip(),
                new_status=new_status,
                event_timestamp=event_timestamp.strip() or None,
                strict_transition=strict_transition,
            )
            st.success(
                f"Order '{result['order_id']}' updated from "
                f"'{result['old_status']}' to '{result['new_status']}'."
            )
            st.json(result)
            st.session_state["inspected_order_id"] = order_id.strip()
        except Exception as exc:
            st.error(f"Update failed and transaction rolled back: {exc}")


def _render_benchmark_tab() -> None:
    st.subheader("Query Execution Plan & Latency Benchmark")
    if st.button("Run Query Benchmark"):
        try:
            outcome = benchmark_order_queries()
            benchmarks = outcome.get("benchmarks") or []
            if benchmarks:
                st.dataframe(benchmarks, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Benchmark failed: {exc}")


def main() -> None:
    st.title("Order Management")
    st.caption("Module D — Order search, full details, delivery SLA tracking, and transactional updates")

    try:
        summary_rows = get_status_summary()
        _render_overview_metrics(summary_rows)
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Database connection error: {exc}")
        st.stop()

    default_order_id = st.session_state.get(
        "inspected_order_id", "0008288aa423d2a3f00fcb17cd7d8719"
    )

    tab_search, tab_detail, tab_update, tab_bench = st.tabs(
        ["Order Search", "Order Detail & SLA", "Status Update", "Query Benchmark"]
    )

    with tab_search:
        _render_order_search_tab()

    with tab_detail:
        _render_detail_and_tracking_tab(default_order_id)

    with tab_update:
        _render_status_update_tab(default_order_id)

    with tab_bench:
        _render_benchmark_tab()


if __name__ == "__main__":
    main()
