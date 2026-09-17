# V&V Toolchain Prototype

A small learning project for explaining requirements, testing, traceability, and reporting in an interview. All records are fictional; these files are simplified stand-ins for Jama, TestRail, and Jira, not their actual API schemas.

## Step 1: Define the data and its relationships

The goal of this step is to answer three questions using a small, readable dataset: which requirements have tests, which tests failed, and which defects relate to those failures. We created three JSON files. There is no Python code, database, API, or dashboard yet.

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

These IDs are plain JSON values at this stage. Later validation and database rules will check that they are unique where required and point to existing records.

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

Expected totals: **3 requirements, 3 tests, 1 defect, and 1 uncovered requirement**. JSON parsing, record counts, valid links, and the expected coverage gap were checked when these files were created. Automated quality checks will be added in a later step.

## Next increments

1. Load these files into SQLite with Python and query uncovered requirements.
2. Add data-quality checks for missing IDs, invalid statuses, duplicate IDs, and broken links.
3. Serve the sample data through local REST endpoints and build a small sync client.
4. Add timeouts, safe retries, repeatable loading, and sync outcome reporting.
5. Build a dashboard with clearly defined metrics and supporting detail.

Only Step 1 is implemented. Each increment will include the reason for the change, a small verification, and an interview explanation. Ford's L2/L3/L4 definitions would need to be confirmed before modeling those testing levels.
