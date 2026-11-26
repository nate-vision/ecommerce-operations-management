# Restructuring verification — A + B integration

## Environment
Python 3.13.5; SQLite 3.46.1; pandas 2.2.3; numpy 2.3.5; matplotlib 3.10.8; Linux. Windows and Streamlit runtime not verified here.

## Actual results

| Check | Result | Evidence |
|---|---|---|
| Original database, schema, seller/customer SQL and 9 raw CSV files | PASS | Byte-identical SHA-256 comparison |
| Python source compilation | PASS | compileall, all delivered Python files |
| Customer backend, original DB | PASS | 7/7 tests; 3.876 s in benchmark run |
| Customer CLI from unrelated cwd | PASS | Six commands returned 20, 1, 1, 17, 1, 1 rows |
| Backend test script from unrelated cwd | PASS | 7/7 tests |
| Seller analysis from unrelated cwd | PASS | 3,095 seller rows and 22 state rows match original CSVs (numeric tolerance); 5 PNGs regenerated and verified readable |
| Seller SQL | PASS | View plus seven queries executed in isolated copy; rows 10, 22, 5, 10, 1, 24, 1 |
| Rebuild from CSV in independent folder | PASS | All 10 tables, matching row counts and two-way EXCEPT comparisons (coordinates rounded to 10 decimal places) |
| Rebuilt DB integrity and foreign keys | PASS | integrity_check ok; foreign_key_check empty |
| Customer backend, rebuilt DB | PASS | 7/7 tests |
| Q1 performance comparison | PASS | Equal results; nine warm-cache full-fetch repetitions |
| Streamlit page + navigation / browser and AppTest | BLOCKED | Streamlit not installed; pip could not obtain dependency, ModuleNotFoundError. Run locally. |

Original A CSV results and chart assets are retained; generated seller outputs were compared during testing. Original Stage 2 benchmark is retained as `results/customer/raw/customer_benchmark_stage2.csv`. The original post-migration benchmark is now archived at `results/customer/raw/customer_benchmark_restructured.csv`.

## Query benchmark

| Query | Rows | Median (ms) |
|---|---:|---:|
| Q1 baseline | 20 | 637.197402 |
| Q1 optimized | 20 | 0.376208 |
| Q2 | 1 | 0.376708 |
| Q3 | 1 | 0.061283 |
| Q4 | 17 | 0.155004 |
| Q5 | 1 | 0.058148 |
| Q6 | 1 | 0.037176 |

Q1 speedup 1693.74x for the tested first-page scenario only, same database and connection, excludes connection/Pandas/browser rendering. No schema/index changes. Other queries, broad filters, cold caches and larger data sizes may differ.

## Reproduce locally (project root)

```powershell
python -m pip install -r requirements.txt
python -m compileall -q app.py database modules pages scripts tests
python -m modules.seller.seller_analysis
python -m tests.test_customer --benchmark --runs 9 --output results/customer/customer_benchmark_new.csv
python -m tests.test_customer_ui
python -m streamlit run app.py
```

To test the standalone launcher, stop the running app and use `python -m streamlit run scripts/customer_app.py`. Test only delivered Customer UI; no Seller/Product/Order/Payment & Review UI supplied. Initialize a database if absent; do not rebuild an existing database for a routine launch. To test the loader, copy the entire project to a separate folder and run `python database/load_to_sqlite.py` there (deletes existing DB).

## Change scope

A: only filesystem paths adjusted in loader and analysis; all data and SQL unchanged. B: paths/imports, benchmark destination and standalone launcher adapted; core six queries and business logic unchanged. New shared entry, theme, package markers and folder conventions. Stage 3 dependencies merged into root requirements. TeamForming.docx not copied into shared deliverable; keep original privately. Reserved C–E folders contain package markers only. No remote repository or member access created.

Historical restructuring check: local Git add, commit and clone passed (39 tracked files; raw data and database excluded at that time). The current upload-ready version includes raw data and excludes the generated database and other ignored files. No remote GitHub upload performed.
