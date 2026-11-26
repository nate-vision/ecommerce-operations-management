# Team development guide

SDSC5003 — E-Commerce Operations Management System (Track 1)

## Shared project contract

- Keep A's existing schema and business logic in `database/` and `modules/seller/`; use the relocated database path. Coordinate any future schema changes with the team.
- Use Python and SQLite (`database/olist.db`). Streamlit is the selected integration proposal; confirm it with the team.
- If Streamlit is agreed, keep business functions separate from UI pages, use English labels and let the shared launcher control navigation and page configuration. Do not replace another member's files.
- The repository includes source code, SQL, tests, recorded results and the nine original Olist CSVs under `data/`. Keep `database/olist.db` outside Git tracking. Do not modify the shared raw CSV files. See `data/README.md` for attribution and license. If the CSVs are missing, obtain them from https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce.
- Run `python database/load_to_sqlite.py` only to initialize or deliberately rebuild a local database. It deletes the existing `olist.db`; back it up first if needed.
- Do not commit secrets, personal team documents or dataset archives. Cite external resources and snippets.

## Branches

| Member | Branch | Responsibility |
|---|---|---|
| A | feature/database-seller | Database and seller |
| B | feature/customer | Customer module, GitHub, README |
| C | feature/product | Product catalog |
| D | feature/order | Order management |
| E | feature/payment-review | Payment and review analytics |
| F | feature/documentation | Documentation and video |

These branch names are conventions, not a change to the original division of work.

## Workflow (PowerShell)

Clone the repository once, then start your branch from the current main branch:

```powershell
git clone https://github.com/YOUR_USERNAME/ecommerce-operations-management.git
cd ecommerce-operations-management
git switch main
git pull --ff-only origin main
git switch -c feature/YOUR_MODULE
```

Use your real GitHub URL and branch name. If your branch already exists, use `git switch feature/YOUR_MODULE` (or `git switch --track origin/feature/YOUR_MODULE` for an existing remote branch).

Install dependencies, verify that the nine CSVs are present in `data/`, and initialize a fresh local database only if absent:

```powershell
python -m pip install -r requirements.txt
if (-not (Test-Path .\database\olist.db)) { python database/load_to_sqlite.py }
```

Review and commit only your own intended changes. For example, Member B:

```powershell
git status
git add modules/customer/ tests/test_customer.py tests/test_customer_ui.py pages/02_Customer.py scripts/customer_app.py
git diff --cached --stat
git commit -m "Implement customer management module"
git push -u origin feature/customer
```

Open a pull request into `main`. Review changes, run relevant tests and resolve conflicts together before merging. Do not force-push or delete shared history. If A's work is initially imported by B, identify A as the original contributor in the commit description/report; do not impersonate A's Git identity.

## Before opening a pull request

- Module runs with the shared database.
- Include SQL, Python source and UI page (if agreed), plus relevant tests.
- Update dependency list or usage instructions if necessary, coordinating shared-file edits.
- Provide a short summary, test results and screenshots as appropriate.
- Keep benchmarks reproducible; record real measurements and the environment.

Current B validation commands:

```powershell
python -m tests.test_customer
python -m tests.test_customer --benchmark --runs 9 --output results/customer/customer_benchmark_new.csv
python -m streamlit run scripts/customer_app.py
python -m tests.test_customer_ui
```

The root README and common app launcher are included; C–E and A’s front-end page are pending. Confirm the instructor can access the final repository before submission.
