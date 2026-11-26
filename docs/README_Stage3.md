# Stage 3 — Customer UI (Member B)

This describes the relocated Customer page in the integrated project. It uses the original SQLite database and the six existing customer services. A and B business logic is unchanged; paths have been adapted. The UI is read-only.

## Setup

Run from the project root containing `app.py`. The database is `database/olist.db` and the business files are in `modules/customer/`.

```powershell
python -m pip install -r requirements.txt
if (-not (Test-Path .\database\olist.db)) { python database/load_to_sqlite.py }
python -m streamlit run scripts/customer_app.py
```

Open the Local URL printed in the terminal (normally http://localhost:8501). Stop with Ctrl+C. If the team already has a common entry point, use that instead.

## Demonstration

1. Browse the first page (20 customers). Click Next and Previous.
2. Enter `8d50f5` in Customer ID / prefix, choose `SP`, click Search. Exactly one customer is expected in the original dataset.
3. Select `8d50f5eadf50201ccdcedfb9e2ac8455`, click View customer. Expect 17 orders, 15 delivered, R$ 879.27 delivered spend.
4. Choose order `d3582fd5ccccd9cb229a63dfb417c86f` in the order selector. Expect one item, price R$ 23.40, freight R$ 15.26, item total R$ 38.66.
5. Change state to RJ while retaining the same prefix and click Search. No matching customers should be displayed.
6. Click Refresh page to re-fetch the current list if database contents have changed. Search filters and pagination use the existing backend SQL. An exactly full final page may enable Next; an empty next page can be navigated back from.

## Tests

```powershell
python -m tests.test_customer
python -m tests.test_customer_ui
```

The UI test uses Streamlit AppTest; it requires Streamlit installed locally. For SQL benchmark results, continue using `python -m tests.test_customer --benchmark --runs 9 --output results/customer/customer_benchmark_new.csv`. The time shown in the page is a single last-fetch time (includes Python and database access), not the SQL benchmark median. It is not browser rendering time.

## Team integration

The page does not call `st.set_page_config()` or define team-wide navigation. Add this entry to the existing team's `st.navigation([...])` list:

```python
st.Page('pages/02_Customer.py', title='Customer', icon=':material/group:')
```

Or use the conventional `pages/` directory if the team uses automatic multipage discovery. `customer_app.py` is just a standalone launcher, not a replacement for the team's `app.py`. Keep the relocated files in `modules/customer/` and `database/`. UI dependencies are merged into the root requirements. No HTTP API, external payment, or customer writes are implemented.
