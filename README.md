# V&V Toolchain Prototype

A small interview prototype that simulates requirements from Jama, tests from TestRail, and defects from Jira. It validates the records, stores them in SQLite, and displays coverage, traceability, and release-readiness results in a browser.

For the function-by-function call order, read [End-to-End Application Flow](END_TO_END_FLOW.md).

## Application flow

```text
Sample JSON -> Tool-named API endpoints -> validation -> SQLite -> dashboard
```

The records connect through stable IDs:

```text
Requirement -> Test -> Defect
REQ-002    -> TEST-002 -> BUG-001
```

## Run the application

No additional packages are required. Open two PyCharm terminals in this project folder.

Terminal 1 starts the server:

```powershell
.\.venv\Scripts\python.exe api.py
```

Keep it running. Terminal 2 loads the data:

```powershell
.\.venv\Scripts\python.exe load_data.py --api-url http://127.0.0.1:8000
```

Expected output includes:

```text
Loaded 3 requirements, 3 tests, and 1 defects into vv.db.
Requirements without tests: 1
REQ-003: Display the rear camera view when reverse is selected
```

Open <http://127.0.0.1:8000/dashboard>. After changing a file in `data/`, rerun the loader and click **Refresh report**. Stop the server with Ctrl+C.

## Main files

| File | Purpose |
| --- | --- |
| `data/*.json` | Fictional requirements, tests, and defects |
| `api.py` | Serves the tool endpoints, report, and dashboard |
| `load_data.py` | Fetches, validates, and loads the SQLite snapshot |
| `data_quality.py` | Checks fields, IDs, statuses, and relationships |
| `reporting.py` | Calculates metrics, traceability, and readiness |
| `dashboard.html` | Displays the report |
| `vv.db` | Generated SQLite database |

## Simulated endpoints

| Endpoint | Purpose |
| --- | --- |
| `/jama/requirements` | Requirements |
| `/testrail/tests` | Tests |
| `/jira/defects` | Defects |
| `/report` | Dashboard report data |
| `/dashboard` | Browser dashboard |

These endpoints use a simplified shared schema. Real integrations would add authentication, pagination, rate limits, retries, and organization-specific mappings.

## Validation and database behavior

Before opening SQLite, the loader checks required fields, duplicate IDs, allowed statuses, requirement-to-test links, and test-to-defect links. Invalid input leaves the existing database unchanged.

Valid data replaces the snapshot in one transaction. Primary keys prevent duplicate IDs and foreign keys protect relationships. The loader uses this SQL pattern to find requirements without tests:

```sql
SELECT r.requirement_id, r.title
FROM requirements r
LEFT JOIN tests t ON r.requirement_id = t.requirement_id
WHERE t.test_id IS NULL;
```

## Dashboard and readiness

The dashboard shows requirement coverage, test execution, pass rate, open defects, records needing attention, and requirement-to-test-to-defect traceability.

The demo reports ready only when requirements and tests exist, every requirement has a test, every planned test passed, no high or critical defect remains open, and the snapshot passes validation. These are example rules, not official Ford policy.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

## Interview explanation

> I built a small V&V pipeline that simulates Jama, TestRail, and Jira with three local REST endpoints. A Python loader validates the records before replacing a SQLite snapshot in one transaction. The reporting layer calculates coverage, execution, defects, traceability, and readiness blockers, and a browser dashboard displays the results.

Production improvements would include authentication, pagination, retries, incremental synchronization, execution history, scheduled jobs, and approved release rules.
