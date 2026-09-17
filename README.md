# V&V Toolchain Prototype

A small learning project for explaining requirements, testing, traceability, and reporting in an interview. All records are fictional; these files are simplified stand-ins for Jama, TestRail, and Jira, not their actual API schemas.

## Step 1: Define the data and its relationships

The goal of this step is to answer three questions using a small, readable dataset: which requirements have tests, which tests failed, and which defects relate to those failures. Step 1 creates the JSON files, Step 2 adds SQLite, Step 3 adds validation, and Step 4 adds a local API. Steps 5 and 6 below add vendor-shaped mocks and a browser dashboard.

This supports the job description's focus on **test data standardization** and **requirements-to-test traceability**. Defining consistent fields and links first gives later integrations and reports a common structure.

| File | Represents | Key relationship |
| --- | --- | --- |
| `data/requirements.json` | Requirements, like those managed in Jama | Each requirement has a stable `requirement_id`. |
| `data/tests.json` | Test cases with a current result, like those managed in TestRail | `requirement_id` links each test to a requirement. |
| `data/defects.json` | Defects, like those managed in Jira | `test_id` links each defect to a test. |

The relationship is **Requirement -> Test -> Defect**. IDs establish the links; matching titles is unnecessary. A requirement can have multiple tests, and a test can have multiple defects. For this first step, each test links to one requirement and stores only its current status. Execution history and tests covering multiple requirements would need additional tables later.

### What each field means

| File | Fields and purpose |
| --- | --- |
| `requirements.json` | `requirement_id`: unique requirement identifier; `title`: expected behavior; `release`: release the requirement belongs to (`DEMO-1`). |
| `tests.json` | `test_id`: unique test identifier; `requirement_id`: requirement being checked; `title`: description of the check; `status`: current test outcome or execution state. |
| `defects.json` | `defect_id`: unique defect identifier; `test_id`: test that exposed the problem; `title`: problem description; `severity`: seriousness of the problem; `status`: current defect workflow state. |

These IDs are plain values in the JSON files. Step 2 adds database rules for unique IDs and valid links. Step 3 adds readable data-quality errors before loading.

### The exact sample relationships

| Requirement | Expected behavior | Linked test | Test status | Linked defect |
| --- | --- | --- | --- | --- |
| `REQ-001` | Lock doors on request | `TEST-001` | `PASS` | None |
| `REQ-001` | Lock doors on request | `TEST-003` | `NOT_RUN` | None |
| `REQ-002` | Warn about low tire pressure | `TEST-002` | `FAIL` | `BUG-001`: `HIGH`, `OPEN` |
| `REQ-003` | Display rear camera view in reverse | None | No test exists | None |

For example, `TEST-002.requirement_id` contains `REQ-002`, and `BUG-001.test_id` contains `TEST-002`. Following those fields connects the missing tire-pressure warning to the test that found it and the requirement it affects.

### Why these records?

- `REQ-001` has one passing test and one test that has not run. Linked coverage does not mean all testing is complete.
- `REQ-002` has a failing test linked to an open high-severity defect. We can trace a problem back to the requirement it affects.
- `REQ-003` has no test. This deliberately demonstrates a coverage gap.

There are three requirements and three tests, but only two requirements have linked tests: **2 / 3 = 66.7% coverage**. A test count alone cannot tell us coverage.

For this prototype, test statuses are `PASS`, `FAIL`, `BLOCKED`, and `NOT_RUN`. Defect statuses are `OPEN`, `IN_PROGRESS`, and `CLOSED`. Agreeing on field names and meanings makes future validation and reporting consistent.

### How to explain this in an interview

“I started by defining the relationships between requirements, tests, and defects. Stable IDs let me trace a failed test back to its requirement and associated defect. I deliberately included an uncovered requirement and an unrun test to show why coverage and successful validation are different measures.”

### Check this step

No dependencies or running services are needed. Open the files in your editor and check:

1. In `requirements.json`, find `REQ-002` and read its expected behavior.
2. In `tests.json`, find the test whose `requirement_id` is `REQ-002`: `TEST-002`, with status `FAIL`.
3. In `defects.json`, find the defect whose `test_id` is `TEST-002`: `BUG-001`, with severity `HIGH` and status `OPEN`.
4. Search `tests.json` for `REQ-003`. It should have no matches, demonstrating missing coverage.
5. Find both tests for `REQ-001`. One passed and one has not run, demonstrating that linked coverage does not guarantee completed testing.

Expected totals: **3 requirements, 3 tests, 1 defect, and 1 uncovered requirement**. JSON parsing, record counts, valid links, and the expected coverage gap were checked when these files were created. Step 3 adds automated quality checks.

## Step 2: Load SQLite and query missing coverage

**Goal:** replace manual inspection with a repeatable Python load and a SQL query. This demonstrates the JD's Python automation, SQL extraction, and traceability reporting requirements.

### What was added and why

`load_data.py` uses only Python's standard library, so no packages need to be installed. It creates `vv.db` beside the script. SQLite stores relational tables in one local file without requiring a database server. The generated database is already excluded from Git by `.gitignore`.

```text
data/*.json -> load_data.py -> vv.db -> uncovered requirements printed in terminal
```

| Part of the script | What it does | Why it matters |
| --- | --- | --- |
| `read_records()` | Reads each JSON file relative to the script's location. | Input paths work even when the script is launched from a different folder. |
| `create_tables()` | Creates requirements, tests, and defects tables with primary and foreign keys. | Primary keys reject duplicate IDs; enabled foreign keys reject broken links. |
| `load_snapshot()` | Replaces all three tables' records in one transaction, using parameterized inserts. | Reruns do not accumulate duplicates, values are kept separate from SQL, and a failed load rolls back record changes. |
| `find_uncovered_requirements()` | Runs a `LEFT JOIN` and selects requirements with no matching test. | Finds coverage gaps without manually comparing every requirement and test. |
| `main()` | Reads inputs, enables foreign keys, loads records, and prints the report. | Provides one command to run the complete step and closes the database connection afterward. |

This is a **full snapshot refresh**, suitable for this small demo. Every run replaces stored records with the current JSON contents, including removing rows no longer present in the files. Children are deleted before parents; parents are inserted before children. It is not an incremental sync or a migration checkpoint system.

### The SQL explained

```sql
SELECT r.requirement_id, r.title
FROM requirements r
LEFT JOIN tests t ON r.requirement_id = t.requirement_id
WHERE t.test_id IS NULL
ORDER BY r.requirement_id;
```

1. `FROM requirements` starts with the requirements we want to check.
2. `LEFT JOIN` retains every requirement, even when it has no matching test.
3. `WHERE t.test_id IS NULL` keeps only those unmatched requirements. Stored test IDs cannot be null.
4. `ORDER BY` makes the output predictable.

The script also creates an index on `tests(requirement_id)` to support lookups by the join key. This is a useful foundation, not evidence that the prototype has been tested at millions of records.

### Run this step

In the PyCharm terminal, from this project folder:

```powershell
.\.venv\Scripts\python.exe load_data.py
```

Alternatively, run `load_data.py` in PyCharm with the project's configured interpreter. Expected output:

```text
Loaded 3 requirements, 3 tests, and 1 defects into vv.db.

Requirements without tests: 1
REQ-003: Display the rear camera view when reverse is selected
```

Run it again: the counts and uncovered requirement should stay the same. `REQ-001` and `REQ-002` are covered because they have linked tests, even though one test has not run and another failed. This query measures linked coverage, not release readiness.

If an input file is missing or contains invalid JSON, reading fails before the database load. If a record violates a database constraint during loading, the script raises an error and rolls back that snapshot refresh. Step 3 adds detailed validation messages and status checks before the connection is opened.

### How to explain this in an interview

“I wrote a Python script to load requirements, tests, and defects into SQLite. Primary and foreign keys protect the identifiers and relationships. I load the data in one transaction, then use a LEFT JOIN to report requirements without tests. Rerunning refreshes the snapshot without creating duplicates.”

## Step 3: Check data quality before loading

**Goal:** identify bad input with actionable messages before it reaches SQLite. This supports the JD's test data standardization, compliance checks, and reduction of manual cleanup work.

### What changed and why

- `data_quality.py` adds `validate_data()`, which returns a list of problems without changing records or connecting to SQLite. Separating these checks lets a future API integration reuse them.
- `load_data.py` calls the validator after reading the three files and before opening the database. If there are errors, it prints them together and exits with code `1`. Successful runs exit with code `0`, which future automation can use to detect success or failure.
- `test_data_quality.py` checks valid data, invalid data, and the rule that rejected input never opens the database. It uses Python's built-in `unittest`; no new packages are needed.

```text
JSON files -> read records -> validate
                                |
                     errors ----+---- valid
                       |                |
                 print issues      load SQLite
                 stop safely       report coverage
```

### Checks included

| Check | Example rejected input | Why it matters |
| --- | --- | --- |
| File structure | A JSON object instead of an array, or a non-object row | The loader expects a list of records. |
| Required fields | Missing, null, blank, or non-string ID, title, release, status, or severity where that field is required | Prevents incomplete records and incompatible field types. |
| Duplicate IDs | Two tests both named `TEST-001` by their ID | Each entity needs a unique source identifier. IDs are checked separately for requirements, tests, and defects. |
| Test statuses | `Passed` instead of `PASS` | Reports need consistent values: `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`. |
| Defect statuses | `DONE` instead of `CLOSED` | Allowed values are `OPEN`, `IN_PROGRESS`, and `CLOSED`. |
| Test-to-requirement links | A test references `REQ-MISSING` | Traceability must point to an existing requirement in the input snapshot. |
| Defect-to-test links | A defect references `TEST-MISSING` | Defects must point to an existing test in the input snapshot. |

The validator uses sets to track IDs and check links rather than repeatedly scanning all parent records. Error messages identify the file, row number (starting at 1), and problem.

Database constraints remain in place as a second safeguard. The validator adds readable messages, checks statuses that the current database schema does not constrain, and reports multiple issues in one run.

### Run and try it

Run the same command as Step 2:

```powershell
.\.venv\Scripts\python.exe load_data.py
```

The existing sample data passes, so the output remains the same. A failed test, an unrun test, and an uncovered requirement are valid data describing testing risks; they are not malformed records.

To see an error, temporarily change the first test's status in `data/tests.json` from `PASS` to `Passed`, save, and run again:

```text
Data quality check failed: 1 issue(s)
- tests.json row 1: invalid status 'Passed'; expected one of BLOCKED, FAIL, NOT_RUN, PASS
Database not changed.
```

Restore `PASS` afterward. Validation does not automatically normalize, delete, or repair anything. All three files must pass before any database writes occur.

Run the automated checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_data_quality
```

### Scope of this step

These are prototype data-quality rules, not a claim of regulatory compliance. Severity must be a nonblank string, but an allowed severity list has not been defined yet. IDs are compared exactly; records are not silently trimmed or renamed. Empty arrays are allowed as full snapshots, so three empty arrays would clear the stored records. Step 4 adds readable source-error reporting for missing files and invalid JSON before database loading.

### How to explain this in an interview

“I added validation before loading the data. It checks required fields, duplicate IDs, allowed statuses, and requirement-to-test and test-to-defect links. It reports all detected issues with file and row details, and stops before opening the database if any checks fail. That gives someone clear corrections to make without replacing the last loaded data.”

## Step 4: Read sample data through a local REST API

**Goal:** demonstrate HTTP integration while reusing the validation, database loading, and coverage query already built.

### Minimal changes and why

- `api.py` serves three read-only GET endpoints: `/requirements`, `/tests`, and `/defects`. Each returns the corresponding JSON file. This simulates fetching engineering data from other tools without needing accounts.
- `load_data.py` adds `fetch_records()` and an optional `--api-url` argument. It reads the HTTP responses as JSON, then follows the same validation and database workflow. Running without the argument still reads local files.
- Requests have a 10-second socket timeout. HTTP errors, connection errors, and invalid JSON stop the load before opening SQLite and return exit code `1`. There are no automatic retries yet.

Both files use only Python's standard library. The server binds to `127.0.0.1` for local use. This is a small learning server with simplified endpoints, not a production service or an implementation of the vendors' actual APIs. Authentication, pagination, and coordinated snapshots across requests are not implemented.

```text
JSON files -> local HTTP API -> fetch_records -> validate -> SQLite -> coverage report
```

### Run this step

Open two terminals in the project folder. In terminal 1:

```powershell
.\.venv\Scripts\python.exe api.py
```

Leave it running. Open <http://127.0.0.1:8000/requirements> in your browser to see the requirements JSON. `/tests` and `/defects` expose the other records; unknown paths return HTTP 404.

In terminal 2:

```powershell
.\.venv\Scripts\python.exe load_data.py --api-url http://127.0.0.1:8000
```

The result is still three requirements, three tests, one defect, and `REQ-003` as the only uncovered requirement. Only the way we obtain the records has changed.

Stop the server with Ctrl+C in terminal 1. Running the API load again should report a source error and `Database not changed.` Start the server again to retry. If port 8000 is already occupied, stop the previous server using that port before starting this one.

### How to explain this in an interview

“I added a local REST API to simulate engineering tools. The loader requests requirements, tests, and defects over HTTP, validates the returned JSON, and loads the same reporting database. I kept data retrieval separate from validation and SQL so both file and API inputs reuse the same processing logic.”

## Step 5: Mock vendor formats and map them into our schema

**Why:** real tools return different field names, nesting, identifiers, and pagination formats. An integration needs to translate them before validation and reporting.

`vendor_mocks.py` converts the existing fictional JSON records into small vendor-shaped responses. `integrations.py` fetches each page and translates the responses back into our shared schema. The old file mode and simple API mode still work. No dependencies were added.

| Mock endpoint | Pattern demonstrated | Mapping into this demo |
| --- | --- | --- |
| `/mock/jama/rest/v1/items?startAt=0&maxResults=2` | `data`, `fields`, and `meta.pageInfo` with indexed pagination | `documentKey` becomes requirement ID; `fields.name` becomes title. |
| `/mock/testrail/index.php?/api/v2/get_tests/1&offset=0&limit=2` | Tests in run 1, numeric status IDs, references, and `_links.next` | `refs` becomes requirement ID; statuses 1, 2, 3, 5 become PASS, BLOCKED, NOT_RUN, FAIL. |
| `/mock/jira/rest/api/3/search/jql?maxResults=2` | Issue keys, nested `fields`, and `nextPageToken` pagination | `key` becomes defect ID; `summary` becomes title; workflow names map to our statuses. |

Pages contain at most two records by default so even the small sample exercises pagination. Repeated page locations stop the adapter rather than looping forever. Unknown status mappings and multiple requirement references stop the load rather than being guessed or silently discarded.

### What is realistic and what is simulated?

The response structures and pagination patterns are based on the [Jama-maintained Python client](https://jamasoftware-ps.github.io/py-jama-rest-client/py_jama_rest_client/client.html), [TestRail tests API](https://support.testrail.com/hc/en-us/articles/7077990441108-Tests), and [Jira Cloud issue search API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/).

These are documented subsets, not complete vendor emulators or live connectors:

- `/mock/jama`, `/mock/testrail`, and `/mock/jira` are local routing prefixes, not vendor URLs.
- Jama `release_demo`, TestRail `custom_source_id`, and Jira `customfield_10001` are demo field conventions. TestRail's numeric test ID and case ID are shown separately; the custom field preserves this project's existing `TEST-001` identifiers.
- Jira priority is used as a severity proxy only for this demo. Real priorities and defect severity may be different fields. Workflow names and custom fields vary by organization.
- The mock returns all sample Jira issues and Jama items; it does not evaluate JQL or project filters. TestRail exposes only run 1 and current test statuses, not execution history.
- No credentials, authentication, permissions, retries, rate-limit simulation, or live writes are implemented. The original JSON files remain the mock source of truth.
- To connect real systems, configure separate service URLs and approved authentication, discover project/run and custom-field IDs, define mappings and scope filters, and add robust contract tests against those environments. Changing only the base URL is not sufficient.

### Run the vendor mock load

Restart `api.py` if it is already running, so it picks up the new routes. In terminal 1:

```powershell
.\.venv\Scripts\python.exe api.py
```

In terminal 2:

```powershell
.\.venv\Scripts\python.exe load_data.py --api-url http://127.0.0.1:8000 --vendor-mocks
```

Expected result: the same three requirements, three tests, one defect, and `REQ-003` coverage gap. All pages from all three services are collected and validated before the database is refreshed.

Interview explanation: “I isolated tool-specific response formats in adapters. Each adapter handles pagination and maps fields into a common model, so validation and reporting do not depend on which system supplied the data.”

## Step 6: Mock BI dashboard and release-readiness report

**Why:** counts need definitions and supporting records to help someone decide what still needs attention.

Open <http://127.0.0.1:8000/dashboard> after starting the API and loading the data. The same server now serves `dashboard.html` and a read-only `/report` endpoint. `reporting.py` reads SQLite in one consistent snapshot, scopes records to the selected release, and builds the metrics and readiness checks.

The dashboard offers:

- Release selection and cards for requirements, coverage, execution, pass rate, and open defects.
- Horizontal coverage and test-status charts with numeric labels.
- Explicit pass/block reasons for every readiness rule.
- Details for uncovered requirements, tests needing attention, and open defects.
- Searchable requirement-to-test-to-defect traceability and a CSV export of all traceability rows in the selected release scope. The text search only filters the visible table, not the export.
- The last successful load timestamp and a manual Refresh report button. Refresh reads SQLite; rerun the loader first to ingest changes to the source files.

### Metric definitions and sample values

| Metric | Definition | Existing sample |
| --- | --- | --- |
| Requirement coverage | Distinct requirements with linked tests / in-scope requirements | 2 / 3 = 66.7% |
| Test execution | PASS plus FAIL / planned tests | 2 / 3 = 66.7% |
| Pass rate | PASS / executed tests | 1 / 2 = 50% |
| Open defects | Defects whose status is not CLOSED, including IN_PROGRESS | 1 |

BLOCKED and NOT_RUN are incomplete under this demo's execution definition. Zero denominators display N/A. Metrics are calculated from entity records, not the expanded traceability join, so multiple defects do not inflate test counts.

### Demo readiness rules

Every rule must pass:

1. At least one requirement and one planned test exist in scope.
2. Every requirement has a linked test.
3. Every planned test passed; failed, blocked, or unrun tests prevent readiness.
4. No HIGH or CRITICAL defect remains OPEN or IN_PROGRESS.
5. The loaded snapshot passes field/link validation, and scoped defect severities are recognized as LOW, MEDIUM, HIGH, or CRITICAL.

The original sample correctly displays **NOT READY UNDER DEMO RULES**. Its blockers are the uncovered camera requirement, one failed test, one unrun test, and an open HIGH defect. A missing database shows instructions rather than a ready result; an empty or unknown release scope is not ready. The load timestamp is informational and is stored in the same transaction as the refreshed data. No age-based readiness policy is assumed.

These are illustrative rules, not Ford policy, formal compliance certification, or a complete release approval process. A recent load does not prove recent source executions. The prototype still lacks requirements baselines, execution history, evidence attachments, risk acceptance, sign-offs, and Ford-specific L2/L3/L4 and DVP&R criteria. This is a custom BI-style browser dashboard, not an actual Power BI report.

### Verify this increment

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Tests cover vendor pagination and mapping over real local HTTP, the report endpoint, sample KPIs, release filtering, multiple defects per test, ready and blocked states, empty scopes, informational load timestamps, and rejected status mappings. Source files are not changed by these tests.

Interview explanation: “I built a reporting layer with explicit metric denominators and release-readiness rules. Users can filter by release and inspect the requirements, tests, and defects behind each result. A dashboard refresh reads the latest successfully loaded snapshot, while the integration handles fetching and validating source data.”

## Optional future increments

The prototype deliberately uses manual dashboard refresh and no arbitrary freshness cutoff. Vendor-specific adapters stay separate because each service has a different format. Transactions, validation, pagination guards, and tests protect correctness without adding frameworks or dependencies.

Add bounded retries, authenticated live adapters, execution history, and organization-approved release rules as needed. Steps 1 through 6 are implemented; the previously discussed retry step remains optional and is not implemented.
