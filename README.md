# V&V Toolchain Prototype

A small learning project for explaining requirements, testing, traceability, and reporting in an interview. All records are fictional; these files are simplified stand-ins for Jama, TestRail, and Jira, not their actual API schemas.

## Step 1: Define the data and its relationships

Start with the information we need before building integrations.

| File | Represents | Key relationship |
| --- | --- | --- |
| `data/requirements.json` | Requirements, like those managed in Jama | Each requirement has a stable `requirement_id`. |
| `data/tests.json` | Test cases with a current result, like those managed in TestRail | `requirement_id` links each test to a requirement. |
| `data/defects.json` | Defects, like those managed in Jira | `test_id` links each defect to a test. |

The relationship is **Requirement -> Test -> Defect**. IDs establish the links; matching titles is unnecessary. A requirement can have multiple tests, and a test can have multiple defects. For this first step, each test links to one requirement and stores only its current status. Execution history and tests covering multiple requirements would need additional tables later.

### Why these records?

- `REQ-001` has one passing test and one test that has not run. Linked coverage does not mean all testing is complete.
- `REQ-002` has a failing test linked to an open high-severity defect. We can trace a problem back to the requirement it affects.
- `REQ-003` has no test. This deliberately demonstrates a coverage gap.

There are three requirements and three tests, but only two requirements have linked tests: **2 / 3 = 66.7% coverage**. A test count alone cannot tell us coverage.

For this prototype, test statuses are `PASS`, `FAIL`, `BLOCKED`, and `NOT_RUN`. Defect statuses are `OPEN`, `IN_PROGRESS`, and `CLOSED`. Agreeing on field names and meanings makes future validation and reporting consistent.

### How to explain this in an interview

“I started by defining the relationships between requirements, tests, and defects. Stable IDs let me trace a failed test back to its requirement and associated defect. I deliberately included an uncovered requirement and an unrun test to show why coverage and successful validation are different measures.”

### Check this step

Open the three JSON files. Follow `REQ-002` to `TEST-002` and then to `BUG-001`. Find `REQ-003` and confirm that no test references it. No dependencies or running services are needed yet.

## Next increments

1. Load these files into SQLite with Python and query uncovered requirements.
2. Add data-quality checks for missing IDs, invalid statuses, duplicate IDs, and broken links.
3. Serve the sample data through local REST endpoints and build a small sync client.
4. Add timeouts, safe retries, repeatable loading, and sync outcome reporting.
5. Build a dashboard with clearly defined metrics and supporting detail.

Only Step 1 is implemented. Each increment will include the reason for the change, a small verification, and an interview explanation. Ford's L2/L3/L4 definitions would need to be confirmed before modeling those testing levels.
