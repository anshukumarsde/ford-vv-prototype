# End-to-End Application Flow

This document explains which code runs from startup through dashboard display.

```text
data/*.json -> src/api.py endpoints -> src/load_data.py -> src/data_quality.py
                                              -> vv.db
Browser -> src/api.py /report -> src/reporting.py -> vv.db -> src/dashboard.html
```

## 1. Start the server

```powershell
.\.venv\Scripts\python.exe -m src.api
```

Execution order:

1. Python loads `api.py`.
2. It defines the project and database paths and `read_records()`.
3. It imports `build_report()` from `reporting.py`.
4. `api.py` defines `SampleAPIHandler`.
5. `ThreadingHTTPServer` opens `127.0.0.1:8000`.
6. `serve_forever()` waits for requests.

Each GET request calls `SampleAPIHandler.do_GET()`:

```text
/dashboard or /      -> return dashboard.html
/report              -> call reporting.build_report()
/jama/requirements   -> read requirements.json
/testrail/tests      -> read tests.json
/jira/defects        -> read defects.json
other path           -> return HTTP 404
```

Starting the server does not load SQLite.

## 2. Run the loader

```powershell
.\.venv\Scripts\python.exe -m src.load_data
```

### 2.1 Start the loader

The final block calls `main()`. Its default API URL is `http://127.0.0.1:8000`.

### 2.2 Fetch records

`main()` calls:

```text
fetch_records(base_url, "/jama/requirements")
fetch_records(base_url, "/testrail/tests")
fetch_records(base_url, "/jira/defects")
```

Every request follows this call path:

```text
load_data.fetch_records()
  -> urlopen(full_url, timeout=10)
  -> api.SampleAPIHandler.do_GET()
  -> ROUTES selects a JSON filename
  -> api.read_records(filename)
  -> json.load() reads data/*.json
  -> SampleAPIHandler.send_body() returns JSON
  -> fetch_records() parses and returns the list
```

After the three calls, `main()` holds requirements, tests, and defects in memory.

### 2.3 Validate records

`main()` calls `validate_data(requirements, tests, defects)`.

`data_quality.py` checks record types, required fields, duplicate IDs, allowed statuses, test-to-requirement links, and defect-to-test links. If errors exist, `main()` prints them and exits before opening SQLite.

### 2.4 Store the snapshot

If validation passes:

```text
sqlite3.connect("vv.db")
  -> PRAGMA foreign_keys = ON
  -> create_tables(connection)
  -> load_snapshot(connection, requirements, tests, defects)
```

`load_snapshot()` runs one transaction:

```text
DELETE defects
DELETE tests
DELETE requirements
INSERT requirements
INSERT tests
INSERT defects
SAVE load timestamp
COMMIT
```

An error rolls back the transaction. Children are deleted first and parents are inserted first to satisfy foreign keys.

### 2.5 Report uncovered requirements

`find_uncovered_requirements()` runs the SQL `LEFT JOIN`. `main()` prints the results, closes the connection, and exits. The loader does not stay running.

## 3. Open the dashboard

Open <http://127.0.0.1:8000/dashboard>.

### 3.1 Load HTML

```text
Browser GET /dashboard
  -> api.SampleAPIHandler.do_GET()
  -> read dashboard.html
  -> send HTML to browser
```

### 3.2 Request the report

JavaScript at the bottom of `dashboard.html` calls `refresh()`:

```text
refresh()
  -> fetch("/report")
  -> api.SampleAPIHandler.do_GET()
  -> reporting.build_report(DATABASE_PATH, release)
```

Choosing a release changes the URL to `/report?release=DEMO-1`.

### 3.3 Calculate results

`build_report()` opens SQLite in read-only mode and reads requirements, tests, defects, the load timestamp, and joined traceability rows. It then:

1. Rechecks data quality.
2. Applies the release filter.
3. Counts test statuses.
4. Finds covered and uncovered requirements.
5. Finds tests and defects needing attention.
6. Calculates coverage, execution, and pass rate.
7. Evaluates the readiness rules.
8. Returns one report dictionary.

`api.py` serializes the dictionary as JSON.

### 3.4 Render results

```text
dashboard refresh()
  -> response.json()
  -> render()
  -> create cards, bars, readiness checks, and tables
```

The **Refresh report** button repeats this report request. It rereads SQLite but does not rerun the loader.

## 4. Change sample data

```text
Edit and save data/*.json
  -> run python -m src.load_data again
  -> endpoints read the changed files
  -> validation runs
  -> SQLite snapshot is replaced
  -> click Refresh report
  -> dashboard reads the new snapshot
```

## 5. Failure behavior

| Failure | Result |
| --- | --- |
| Server unavailable | Fetch fails and the database remains unchanged |
| Invalid JSON | Source read fails and the database remains unchanged |
| Invalid fields, statuses, or links | Validation stops before SQLite opens |
| Database write fails | Transaction rolls back |
| Dashboard opens before a valid database exists | `/report` returns HTTP 503 and the page displays an error |

## Short interview explanation

> The server exposes three fictional tool endpoints. The loader fetches all records, validates them, and replaces a SQLite snapshot in one transaction. The browser requests a report calculated from that snapshot and displays coverage, execution, defects, traceability, and readiness blockers.

## Interview-ready end-to-end explanation

Use this answer when the interviewer asks you to explain the application:

> I built a small V&V reporting pipeline that simulates integrations with Jama, TestRail, and Jira.
>
> The application starts with three fictional JSON datasets containing requirements, tests, and defects. A local Python server exposes them through separate REST endpoints representing the three tools.
>
> A Python loader calls those endpoints and collects all three datasets. Before writing anything, it validates required fields, duplicate IDs, allowed statuses, and relationships. For example, every test must reference an existing requirement, and every defect must reference an existing test.
>
> If validation fails, the loader reports the problems and leaves the existing database unchanged. If validation succeeds, it replaces the SQLite snapshot in one transaction. Primary keys prevent duplicate IDs, and foreign keys protect the requirement-to-test and test-to-defect relationships.
>
> The reporting layer reads SQLite and calculates requirement coverage, test execution, pass rate, open defects, and release-readiness blockers. It also uses SQL joins to build end-to-end traceability from requirements to tests to defects.
>
> The browser dashboard requests those calculated results from a report endpoint and displays the KPIs, uncovered requirements, tests needing attention, open defects, and traceability.
>
> The overall flow is REST APIs to validation to SQLite to reporting to dashboard. In production, I would replace the fictional endpoints with authenticated Jama, TestRail, and Jira clients and add pagination, retries, incremental synchronization, scheduled execution, and organization-approved readiness rules.

### If asked what happens when you run it

1. Start `src.api`. It serves the three simulated tool endpoints, the report endpoint, and the dashboard.
2. Run `src.load_data`. It fetches, validates, and stores a complete snapshot.
3. Open the dashboard. Its JavaScript requests `/report`.
4. `reporting.py` reads SQLite and returns calculated results.
5. The dashboard renders the metrics and supporting records.

### If asked why it is separated this way

> I separated data retrieval, validation, persistence, reporting, and presentation so each part has one clear responsibility and can change independently. For example, authenticated Jama, TestRail, and Jira clients could replace the simulated endpoints without changing the validation rules, database model, or SQL reporting logic.
