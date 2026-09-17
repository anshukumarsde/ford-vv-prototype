# End-to-End Application Flow

This document explains which code runs from startup through dashboard display.

```text
data/*.json -> api.py endpoints -> load_data.py -> data_quality.py
                                              -> vv.db
Browser -> api.py /report -> reporting.py -> vv.db -> dashboard.html
```

## 1. Start the server

```powershell
.\.venv\Scripts\python.exe api.py
```

Execution order:

1. Python loads `api.py`.
2. It imports paths and `read_records()` from `load_data.py`, plus `build_report()` from `reporting.py`.
3. Importing these files defines their functions. It does not call `load_data.main()`.
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
.\.venv\Scripts\python.exe load_data.py --api-url http://127.0.0.1:8000
```

### 2.1 Parse arguments

`argparse` reads `--api-url` and calls `main(api_url)`.

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
  -> load_data.read_records(filename)
  -> json.load() reads data/*.json
  -> api.send_body() returns JSON
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
  -> run load_data.py again
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
