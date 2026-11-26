import streamlit as st

from modules.payment_review import payment_review_module as prm

st.set_page_config(page_title="Payment & Review")

st.title("Payment & Review Management")

st.header("Payment Summary")

payment_df = prm.get_payment_summary()
st.dataframe(payment_df, use_container_width=True)

st.divider()

st.header("Payment Search")

payment_type = st.selectbox(
    "Payment Type",
    ["All", "credit_card", "boleto", "voucher", "debit_card"]
)

result_df = prm.search_payments(payment_type)

st.dataframe(result_df, use_container_width=True)

st.divider()

st.header("Review Statistics")

review_df = prm.get_review_summary()

st.dataframe(review_df, use_container_width=True)

st.bar_chart(
    review_df.set_index("review_score")
)

st.divider()

st.header("Order Review Lookup")

order_id = st.text_input("Order ID")

if st.button("Search Review"):

    if order_id:

        review_detail = prm.search_review(order_id)

        if len(review_detail):

            st.dataframe(
                review_detail,
                use_container_width=True
            )

        else:
            st.warning("Order not found")