# Upload readiness verification

This check applies to the A + B project archive supplied for repository preparation. It does not certify the unfinished team modules.

## Packaging decisions

- The nine original Olist CSV files, source code, tests, recorded results and Customer report are included. The data CSVs, original schema, loader, seller analysis, customer SQL and business module, Customer page and Word report were checked byte-for-byte against the supplied archive.
- The generated `database/olist.db` is excluded from the upload archive (143,118,336 bytes). It can be rebuilt from the included CSVs; the original uploaded archive is unchanged.
- Python bytecode caches are excluded. Four byte-identical duplicates in `results/customer/` were removed; the canonical experimental records are under `results/customer/raw/`.
- README, contribution guide, data attribution, ignore rules and historical run instructions were synchronized. The benchmark script now defaults to `results/customer/customer_benchmark_new.csv`; no business logic or timing methodology was changed.

## Fresh clone verification

Environment: Linux, Python 3.13.5, SQLite 3.46.1, pandas 2.2.3, NumPy 2.3.5, Matplotlib 3.10.8. Streamlit is absent in this environment.

| Check | Result |
| --- | --- |
| Local Git add, commit and clean clone | PASS |
| Nine original CSV files tracked; generated database ignored | PASS |
| Initialize database from included CSVs in clean clone | PASS |
| All 10 table row counts match original supplied database | PASS |
| SQLite integrity check / foreign key check | PASS: ok / zero violations |
| Python compilation | PASS |
| Customer backend test suite on rebuilt database | PASS: 7 tests, 4.507 s |
| Seller analysis | PASS: 3,095 sellers; revenue R$ 13,591,643.70; both CSV outputs match archived values within numeric tolerance |
| Customer result generation | PASS: benchmark summaries and all six query example CSVs match archived values within numeric tolerance |
| Regenerated chart assets | PASS: five Seller and two Customer PNGs verified readable |
| Streamlit AppTest | BLOCKED: ModuleNotFoundError: No module named 'streamlit' |
| Remote GitHub push / instructor access | NOT PERFORMED |

The original report, recorded benchmark inputs and output figures are retained unchanged. No new performance timings are substituted for the recorded experiments. The clean clone check compared database row counts and integrity; the earlier restructuring check recorded more extensive table-content comparisons (see `TEST_RESULTS.md`).

To finish runtime validation on Windows, follow the root README, then run `python -m tests.test_customer_ui` and `python -m streamlit run app.py` in the installed environment. Add actual UI evidence after validation. Other team pages remain pending.
