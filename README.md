# V&V Toolchain Prototype

A small learning project for explaining requirements, testing, traceability, and reporting in an interview. All records are fictional; these files are simplified stand-ins for Jama, TestRail, and Jira, not their actual API schemas.

## Step 1: Define the data and its relationships

The goal of this step is to answer three questions using a small, readable dataset: which requirements have tests, which tests failed, and which defects relate to those failures. In Step 1, we created three JSON files; Step 2 below adds Python and SQLite. APIs and a dashboard are still future steps.

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

These are prototype data-quality rules, not a claim of regulatory compliance. Severity must be a nonblank string, but an allowed severity list has not been defined yet. IDs are compared exactly; records are not silently trimmed or renamed. Empty arrays are allowed as full snapshots, so three empty arrays would clear the stored records. Missing files and invalid JSON syntax still raise Python errors before database loading.

### How to explain this in an interview

“I added validation before loading the data. It checks required fields, duplicate IDs, allowed statuses, and requirement-to-test and test-to-defect links. It reports all detected issues with file and row details, and stops before opening the database if any checks fail. That gives someone clear corrections to make without replacing the last loaded data.”

## Next increments

1. Serve the sample data through local REST endpoints and build a small sync client.
2. Add timeouts, safe retries, and sync outcome reporting.
3. Build a dashboard with clearly defined metrics and supporting detail.

Steps 1 through 3 are implemented. Each increment includes the reason for the change, a small verification, and an interview explanation. Ford's L2/L3/L4 definitions would need to be confirmed before modeling those testing levels.
