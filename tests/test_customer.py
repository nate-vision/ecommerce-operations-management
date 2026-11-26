"""Functional tests and reproducible SQLite query benchmark for Member B.

Run: python -m tests.test_customer
Benchmark: python -m tests.test_customer --benchmark --runs 9
Optional database: --db path/to/olist.db
"""
import argparse
import csv
from contextlib import closing
from pathlib import Path
import sqlite3
import statistics
import time
import unittest

import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from modules.customer import customer_module as cm

DB = cm.DB_PATH


class CustomerTests(unittest.TestCase):
    def setUp(self):
        self.con = cm.get_connection(DB)
        self.addCleanup(self.con.close)

    def read(self, sql, params=()):
        return pd.read_sql_query(sql, self.con, params=params)

    def test_page_and_baseline(self):
        q = cm.load_queries()['baseline']
        for page in (1, 2, 2400, 4805):
            expected = self.read(q, {"page_size": 20, "offset": (page-1)*20})
            actual = cm.get_customers(page, db_path=DB)
            pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
            self.assertTrue(actual.customer_unique_id.is_unique)
        a = cm.get_customers(1, db_path=DB)
        b = cm.get_customers(2, db_path=DB)
        self.assertEqual(len(a), 20)
        self.assertTrue(set(a.customer_unique_id).isdisjoint(b.customer_unique_id))
        self.assertTrue(cm.get_customers(4806, db_path=DB).empty)

    def test_search(self):
        expected = cm.get_customers(db_path=DB)
        pd.testing.assert_frame_equal(cm.search_customers(db_path=DB), expected)
        target = cm.search_customers("8D50F5", "sp", db_path=DB)
        self.assertEqual(target.customer_unique_id.tolist(), [cm.SAMPLE_CUSTOMER])
        self.assertEqual(int(target.total_orders.iloc[0]), 17)
        self.assertTrue(cm.search_customers(cm.SAMPLE_CUSTOMER, "RJ", db_path=DB).empty)
        region = cm.search_customers(state="SP", db_path=DB)
        self.assertEqual(len(region), 20)
        self.assertTrue(region.state.eq("SP").all())
        self.assertTrue(cm.search_customers(cm.SAMPLE_CUSTOMER, city="SAO PAULO", db_path=DB).city.str.lower().eq("sao paulo").all())
        self.assertEqual(len(cm.search_customers(cm.SAMPLE_CUSTOMER, city="SAO PAULO", db_path=DB)), 1)
        self.assertTrue(cm.search_customers(state="ZZ", db_path=DB).empty)

    def test_details_and_history(self):
        cid = cm.SAMPLE_CUSTOMER
        details = cm.get_customer_details(cid, db_path=DB)
        history = cm.get_customer_orders(cid, db_path=DB)
        self.assertEqual(len(details), 1)
        self.assertEqual(len(history), 17)
        self.assertTrue(history.order_id.is_unique)
        self.assertTrue(history.order_purchase_timestamp.is_monotonic_decreasing)
        self.assertEqual(details.latest_order_date.iloc[0], history.order_purchase_timestamp.iloc[0])
        self.assertEqual(details.first_order_date.iloc[0], history.order_purchase_timestamp.iloc[-1])
        self.assertEqual(details.city.iloc[0], history.city.iloc[0])
        self.assertEqual(history.order_status.value_counts().to_dict(), {"delivered":15,"shipped":1,"unavailable":1})

    def test_summary_and_payment_accuracy(self):
        # Independent aggregation from base tables (not the service SQL).
        ids = [cm.SAMPLE_CUSTOMER]
        ids += self.read("""SELECT DISTINCT c.customer_unique_id FROM customer c
            JOIN orders o ON o.customer_id=c.customer_id
            JOIN payment p ON p.order_id=o.order_id
            GROUP BY c.customer_unique_id, o.order_id HAVING COUNT(*) > 1 LIMIT 10""").customer_unique_id.tolist()
        for cid in ids:
            with self.subTest(customer=cid):
                history = cm.get_customer_orders(cid, db_path=DB)
                summary = cm.get_customer_summary(cid, db_path=DB).iloc[0]
                expected = self.read("""SELECT o.order_id, o.order_status, SUM(p.payment_value) AS amount
                    FROM customer c JOIN orders o ON c.customer_id=o.customer_id
                    LEFT JOIN payment p ON p.order_id=o.order_id
                    WHERE c.customer_unique_id=? GROUP BY o.order_id, o.order_status""", (cid,))
                self.assertEqual(len(history), len(expected))
                joined = history.merge(expected, on=["order_id", "order_status"], validate="one_to_one")
                self.assertEqual(len(joined), len(expected))
                pd.testing.assert_series_equal(joined.payment_amount, joined.amount.round(2), check_names=False, check_dtype=False)
                delivered = expected[expected.order_status.eq("delivered")]
                self.assertEqual(int(summary.total_orders), len(expected))
                self.assertEqual(int(summary.delivered_orders), len(delivered))
                self.assertAlmostEqual(float(summary.delivered_spend), round(delivered.amount.sum(), 2), places=2)
                self.assertEqual(int(summary.delivered_orders_missing_payment), int(delivered.amount.isna().sum()))
        summary = cm.get_customer_summary(cm.SAMPLE_CUSTOMER, db_path=DB).iloc[0]
        self.assertAlmostEqual(float(summary.delivered_spend), 879.27, places=2)

    def test_order_items_and_ownership(self):
        items = cm.get_order_items(cm.SAMPLE_CUSTOMER, cm.SAMPLE_ORDER, db_path=DB)
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(float(items.item_total.iloc[0]), 38.66, places=2)
        other = cm.get_customers(db_path=DB).customer_unique_id.iloc[0]
        self.assertTrue(cm.get_order_items(other, cm.SAMPLE_ORDER, db_path=DB).empty)

    def test_missing_and_invalid_inputs(self):
        missing = "0"*32
        for f in (cm.get_customer_details, cm.get_customer_orders, cm.get_customer_summary):
            self.assertTrue(f(missing, db_path=DB).empty)
            with self.assertRaises(ValueError):
                f("' OR 1=1 --", db_path=DB)
        self.assertTrue(cm.search_customers(missing, db_path=DB).empty)
        for p, s in [(0,20),(1,0),(1,101),(1.5,20)]:
            with self.assertRaises(ValueError):
                cm.get_customers(p, s, db_path=DB)
        with self.assertRaises(ValueError):
            cm.search_customers("*", db_path=DB)
        with self.assertRaises(ValueError):
            cm.search_customers(state="SP'", db_path=DB)

    def test_read_only_and_index_plan(self):
        with self.assertRaises(sqlite3.OperationalError):
            self.con.execute("CREATE TABLE stage2_should_not_exist (id INTEGER)")
        plan = self.con.execute("EXPLAIN QUERY PLAN " + cm.load_queries()[4], {"customer_id":cm.SAMPLE_CUSTOMER}).fetchall()
        detail = " ".join(str(r[3]) for r in plan)
        self.assertIn("idx_customer_profile", detail)
        self.assertIn("idx_orders_customer", detail)


def benchmark(runs, output):
    """Same read-only connection, identical parameters, full fetch; warm cache.
    Alternating execution order limits ordering bias. Excludes pandas and UI.
    """
    queries = cm.load_queries()
    params = {"page_size":20, "offset":0, "customer_id":cm.SAMPLE_CUSTOMER,
              "order_id":cm.SAMPLE_ORDER, "pattern":"8d50f5*", "state":"SP"}
    cases = {"Q1_baseline":queries['baseline'], "Q1_optimized":queries[1],
             "Q2":queries[2].replace("/* REGION_FILTER */", "AND g.state = :state"),
             **{f"Q{i}":queries[i] for i in range(3,7)}}
    timings = {name:[] for name in cases}
    rows = {}
    with closing(cm.get_connection(DB)) as con:
        for name, sql in cases.items():
            rows[name] = con.execute(sql, params).fetchall()
        if rows['Q1_baseline'] != rows['Q1_optimized']:
            raise AssertionError("Q1 outputs differ")
        for i in range(runs):
            names = list(cases) if i % 2 == 0 else list(reversed(cases))
            for name in names:
                start = time.perf_counter_ns()
                result = con.execute(cases[name], params).fetchall()
                elapsed = (time.perf_counter_ns()-start)/1e6
                if result != rows[name]:
                    raise AssertionError(f"Results changed: {name}")
                timings[name].append(elapsed)
        print(f"\nSQLite {sqlite3.sqlite_version}; {runs} warm-cache runs; full fetch; page 1, 20 rows")
        print("Query                  Rows   Median (ms)")
        for name, values in timings.items():
            print(f"{name:22s} {len(rows[name]):4d} {statistics.median(values):13.6f}")
        print(f"Q1 speedup: {statistics.median(timings['Q1_baseline'])/statistics.median(timings['Q1_optimized']):.2f}x")
        for name in ("Q1_baseline", "Q1_optimized", "Q4"):
            print(f"\n{name} execution plan:")
            for row in con.execute("EXPLAIN QUERY PLAN " + cases[name], params):
                print(row[3])
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sqlite_version", "query", "run", "rows", "elapsed_ms"])
            for name, values in timings.items():
                for i, value in enumerate(values, 1):
                    writer.writerow([sqlite3.sqlite_version, name, i, len(rows[name]), f"{value:.6f}"])
        print(f"Raw benchmark timings: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=cm.DB_PATH)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--runs", type=int, default=9)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "customer" / "customer_benchmark_new.csv", help="CSV for raw benchmark times")
    args = parser.parse_args()
    DB = args.db
    if args.runs < 3:
        parser.error("--runs must be at least 3")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CustomerTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.benchmark:
        benchmark(args.runs, args.output)
