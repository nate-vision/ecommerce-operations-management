"""SDSC5003 | Member B: read-only customer services and CLI.

The Stage 1 customer_module.sql is the single source of business SQL.
SQL stays alongside this module; the database lives in database/olist.db.
All inputs are bound parameters; the existing schema and indexes are unchanged.
"""
import argparse
from contextlib import closing
from functools import lru_cache
from pathlib import Path
import re
import sqlite3

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
DB_PATH = PROJECT_ROOT / "database" / "olist.db"
SQL_PATH = BASE_DIR / "customer_module.sql"
SAMPLE_CUSTOMER = "8d50f5eadf50201ccdcedfb9e2ac8455"
SAMPLE_ORDER = "d3582fd5ccccd9cb229a63dfb417c86f"


def get_connection(db_path=DB_PATH):
    """Open an existing database read-only (never create or overwrite it)."""
    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}")
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    return con


def _replace(sql, old, new, count=1):
    if sql.count(old) != count:
        raise ValueError(f"Unexpected Stage 1 SQL format: {old!r}")
    return sql.replace(old, new)


@lru_cache(maxsize=1)
def load_queries():
    """Read the six numbered queries and baseline; bind example literals."""
    source = SQL_PATH.read_text(encoding="utf-8-sig")
    parts = re.split(r"(?m)^-- Q([1-6])\. [^\n]*\n", source.split("-- Evaluation:", 1)[0])
    if len(parts) != 13:
        raise ValueError("Expected six numbered queries in customer_module.sql")
    queries = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}
    for q in (1, 2):
        queries[q] = _replace(queries[q], "LIMIT 20 OFFSET 0", "LIMIT :page_size OFFSET :offset")
    queries[2] = _replace(queries[2], "GLOB '8d50f5*'", "GLOB :pattern")
    queries[2] = _replace(queries[2], "AND g.state = 'SP'", "/* REGION_FILTER */")
    for q in (3, 4, 5, 6):
        queries[q] = _replace(queries[q], f"'{SAMPLE_CUSTOMER}'", ":customer_id", 2 if q == 5 else 1)
    queries[6] = _replace(queries[6], f"'{SAMPLE_ORDER}'", ":order_id")
    baseline = re.search(r"-- Q1 comparison baseline[^\n]*\n/\*\s*(.*?)\s*\*/", source, re.S)
    if baseline is None:
        raise ValueError("Missing Q1 comparison baseline in Stage 1 SQL")
    queries['baseline'] = _replace(baseline.group(1), "LIMIT 20 OFFSET 0", "LIMIT :page_size OFFSET :offset")
    return queries


def _id(value):
    value = str(value).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError("ID must contain exactly 32 hexadecimal characters.")
    return value


def _page(page, page_size):
    if type(page) is not int or type(page_size) is not int or page < 1 or not 1 <= page_size <= 100:
        raise ValueError("Page must be a positive integer; page size must be 1-100.")
    offset = (page - 1) * page_size
    if offset > 2**63 - 1:
        raise ValueError("Page offset exceeds SQLite integer range.")
    return {"page_size": page_size, "offset": offset}


def _read(sql, params, db_path):
    with closing(get_connection(db_path)) as con:
        return pd.read_sql_query(sql, con, params=params)


def get_customers(page=1, page_size=20, *, db_path=DB_PATH):
    """Q1: one row per identity; page first, then enrich with location/count."""
    return _read(load_queries()[1], _page(page, page_size), db_path)


def search_customers(prefix="", state=None, city=None, page=1, page_size=20, *, db_path=DB_PATH):
    """Q2: ID prefix/exact ID and optional latest-location filters.

    Region filters apply before pagination. An unfiltered request uses Q1.
    """
    prefix = str(prefix).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{0,32}", prefix):
        raise ValueError("Customer prefix must contain 0-32 hexadecimal characters.")
    state = str(state).strip().upper() if state is not None else ""
    city = str(city).strip() if city is not None else ""
    if state and not re.fullmatch(r"[A-Z]{2}", state):
        raise ValueError("State must be a two-letter code, such as SP.")
    if not prefix and not state and not city:
        return get_customers(page, page_size, db_path=db_path)
    params = _page(page, page_size)
    params["pattern"] = prefix if len(prefix) == 32 else prefix + "*"
    filters = []
    if state:
        filters.append("AND g.state = :state")
        params["state"] = state
    if city:
        filters.append("AND g.city = :city COLLATE NOCASE")
        params["city"] = city
    sql = load_queries()[2].replace("/* REGION_FILTER */", "\n      ".join(filters))
    return _read(sql, params, db_path)


def get_customer_details(customer_unique_id, *, db_path=DB_PATH):
    """Q3: one row for an existing identity; empty frame if not found."""
    return _read(load_queries()[3], {"customer_id": _id(customer_unique_id)}, db_path)


def get_customer_orders(customer_unique_id, *, db_path=DB_PATH):
    """Q4: all orders, one row per order, including non-delivered statuses."""
    return _read(load_queries()[4], {"customer_id": _id(customer_unique_id)}, db_path)


def get_customer_summary(customer_unique_id, *, db_path=DB_PATH):
    """Q5: order counts, delivered payment total and missing-payment count."""
    return _read(load_queries()[5], {"customer_id": _id(customer_unique_id)}, db_path)


def get_order_items(customer_unique_id, order_id, *, db_path=DB_PATH):
    """Q6: order items, restricted to orders belonging to the given identity."""
    return _read(load_queries()[6], {"customer_id": _id(customer_unique_id), "order_id": _id(order_id)}, db_path)


def main():
    parser = argparse.ArgumentParser(description="Customer management (read-only)")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to A's olist.db")
    args = parser.parse_args()
    try:
        with closing(get_connection(args.db)):
            load_queries()
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(1, f"Initialization error: {exc}\n")
    menu = ("\n===== Customer Management =====\n"
            "1. List Customers\n2. Search Customers\n3. Customer Details\n"
            "4. Customer Order History\n5. Customer Spending Summary\n"
            "6. Order Item Details\n0. Exit")
    services = {"3": get_customer_details, "4": get_customer_orders, "5": get_customer_summary}
    while True:
        try:
            print(menu)
            choice = input("Select an option: ").strip()
            if choice == "0":
                break
            if choice in ("1", "2"):
                if choice == "2":
                    prefix = input("Customer ID/prefix (blank = all): ")
                    state = input("State (blank = all): ")
                    city = input("City (blank = all): ")
                page = int(input("Page [1]: ") or "1")
                size = int(input("Page size [20]: ") or "20")
                result = (get_customers(page, size, db_path=args.db) if choice == "1" else
                          search_customers(prefix, state, city, page, size, db_path=args.db))
            elif choice in services:
                result = services[choice](input("Customer unique ID: "), db_path=args.db)
            elif choice == "6":
                result = get_order_items(input("Customer unique ID: "), input("Order ID: "), db_path=args.db)
            else:
                print("Please select 0-6.")
                continue
            print(result.to_string(index=False, na_rep="NULL") if not result.empty else "No matching records.")
            print(f"Returned rows: {len(result)}")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        except (ValueError, OSError, sqlite3.Error, pd.errors.DatabaseError) as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
