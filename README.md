# E-Commerce Operations Management System

SDSC5003 — Track 1: Database Application Development

This project uses the Olist Brazilian E-Commerce dataset to support operational queries for sellers, customers, products, orders, payments and reviews. The application uses SQLite, Python and Streamlit. SQL queries and business functions are kept separate from the UI.

## Current implementation

| Module | Status |
| --- | --- |
| Database and Seller (A) | Ten-table schema, loader, seller queries and analysis available; seller UI pending |
| Customer (B) | Six read-only SQL queries, Python backend, CLI, Streamlit page, tests and performance evaluation available |
| Product (C), Order (D), Payment & Review (E) | Reserved module folders; implementation pending integration |
| Documentation and Video (F) | Final group report and video pending |

Only delivered pages are registered in the shared application. The Customer page is currently available. See [test records](docs/TEST_RESULTS.md) for verified checks and limitations; local browser and UI test evidence should be added after validation.

## Project structure

```text
E-commerce System/
├── app.py                  # Shared Streamlit entry point
├── .streamlit/config.toml   # Shared theme
├── database/               # Schema, loader and generated local database
├── data/                   # Nine original Olist CSVs and data attribution
├── modules/                # SQL and Python business logic by module
├── pages/                  # Streamlit pages
├── tests/                  # Functional and performance tests
├── scripts/                # Standalone launcher and results generation
├── results/                # Recorded experiments, query examples and charts
├── docs/                   # Reports, test records and development guide
├── requirements.txt
└── .gitignore
```

## Quick start (Windows PowerShell)

Open a terminal at the repository root (the directory containing `app.py`). Python 3.11 is recommended. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The repository includes the nine original CSVs under `data/`. The generated SQLite file `database/olist.db` is not tracked by Git. Initialize it only if it does not already exist:

```powershell
if (-not (Test-Path .\database\olist.db)) {
    .\.venv\Scripts\python.exe database/load_to_sqlite.py
    if ($LASTEXITCODE -ne 0) { throw "Database initialization failed" }
}
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://localhost:8501. Stop the application with Ctrl+C.

**Warning:** The original loader deletes an existing `database/olist.db` before rebuilding. Back it up and close the app and DB Browser before deliberately rebuilding. If you retained the original local database, you can copy it to `database/olist.db` instead of rebuilding.

If the raw CSV files are missing, download the original dataset from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place the nine files under `data/` with their original names (see [data information](data/README.md)).

## Module usage

For the remaining commands, activate the virtual environment (`.\.venv\Scripts\Activate.ps1`) or replace `python` with `.\.venv\Scripts\python.exe`. Run from the repository root.

```powershell
python -m modules.seller.seller_analysis
python -m modules.customer.customer_module
python -m streamlit run scripts/customer_app.py
```

The Seller analysis writes CSVs and charts to `results/seller/`. The Customer CLI and page provide customer listing, search, details, historical orders, spending summaries and order items. Customer queries use the existing schema and indexes and a read-only SQLite connection.

To inspect SQL manually, open `database/olist.db` in DB Browser and execute numbered queries in `modules/customer/customer_module.sql` individually. The Seller SQL creates a view; use a practice database copy for DDL.

## Testing and reproducibility

```powershell
python -m compileall -q app.py database modules pages scripts tests
python -m tests.test_customer
python -m tests.test_customer_ui
python -m tests.test_customer --benchmark --runs 9 --output results/customer/customer_benchmark_new.csv
python scripts/generate_customer_results.py
```

The benchmark uses repeated warm-cache SQL execution and full result retrieval. The Q1 comparison uses identical first-page output (20 customers). A new benchmark is written to a separate file to avoid overwriting recorded report inputs. The results-generation script reads the three recorded experiments under `results/customer/raw/` and regenerates summary tables, figures and query examples; it does not rerun the timing experiment or automatically consume `customer_benchmark_new.csv`.

- [Customer technical report](docs/Customer_Module_Report.docx)
- [Recorded benchmark summary](results/customer/benchmark_summary.csv) and [Q1 comparison](results/customer/q1_comparison.csv)
- [Query optimization figure](results/customer/charts/q1_comparison.png) and [local query latency](results/customer/charts/local_query_latency.png)
- [Restructuring verification](docs/TEST_RESULTS.md)
- [Upload readiness verification](docs/UPLOAD_CHECK.md)

Seven backend test groups passed in the recorded verification. The Q1 page-first rewrite was faster than the full-window baseline in three recorded experiments. These measurements describe specified query scenarios, not end-to-end UI latency or all possible search conditions. The restructuring test record did not establish Streamlit runtime success; run the UI tests and record actual results locally.

## Team development

The original division of work is unchanged: A — database and seller; B — customer, GitHub and README; C — product; D — order; E — payment and review; F — documentation and video.

Follow [CONTRIBUTING.md](docs/CONTRIBUTING.md). Use feature branches and pull requests. Each module owns its SQL/Python code and its designated UI page. The shared app controls navigation and theme. Use English labels, parameter binding, existing indexes, database-side filtering and pagination. Coordinate schema, shared dependency and app changes with the team.

The instructor must have access to the final repository. Add the final report and video links once available.

## Data source and references

- Olist, *Brazilian E-Commerce Public Dataset*, [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). The original CSVs are redistributed for non-commercial educational use under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). See [data attribution](data/README.md). The loader processes the source files into a normalized SQLite database; the source CSVs are kept unchanged. Dataset-derived material remains subject to the applicable data license.
- [SQLite documentation](https://sqlite.org/docs.html)
- [Streamlit documentation](https://docs.streamlit.io/)
- A's original project README: [README_A_original.md](docs/README_A_original.md).

Do not commit the generated database, Python cache, virtual environments, secrets, or private team documents. Keep the raw source CSVs and recorded experiment inputs unchanged. Review staged files before committing.
