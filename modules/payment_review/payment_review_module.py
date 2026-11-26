from pathlib import Path
from contextlib import closing
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]

DB_PATH = PROJECT_ROOT / "database" / "olist.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_payment_summary():
    sql = """
    SELECT
        payment_type,
        COUNT(*) AS payment_count,
        ROUND(SUM(payment_value),2) AS total_value,
        ROUND(AVG(payment_value),2) AS avg_value
    FROM payment
    GROUP BY payment_type
    ORDER BY total_value DESC
    """

    with closing(get_connection()) as con:
        return pd.read_sql_query(sql, con)


def get_review_summary():
    sql = """
    SELECT
        review_score,
        COUNT(*) AS review_count
    FROM review
    GROUP BY review_score
    ORDER BY review_score DESC
    """

    with closing(get_connection()) as con:
        return pd.read_sql_query(sql, con)


def search_payments(payment_type="All"):

    if payment_type == "All":
        sql = """
        SELECT
            order_id,
            payment_type,
            payment_installments,
            payment_value
        FROM payment
        LIMIT 100
        """
        params = ()

    else:
        sql = """
        SELECT
            order_id,
            payment_type,
            payment_installments,
            payment_value
        FROM payment
        WHERE payment_type=?
        LIMIT 100
        """
        params = (payment_type,)

    with closing(get_connection()) as con:
        return pd.read_sql_query(sql, con, params=params)


def search_review(order_id):

    sql = """
    SELECT
        r.order_id,
        r.review_score,
        r.review_comment_title,
        r.review_comment_message,
        p.payment_type,
        ROUND(SUM(p.payment_value),2) AS payment_amount
    FROM review r
    LEFT JOIN payment p
        ON r.order_id=p.order_id
    WHERE r.order_id=?
    GROUP BY r.order_id
    """

    with closing(get_connection()) as con:
        return pd.read_sql_query(sql, con, params=(order_id,))