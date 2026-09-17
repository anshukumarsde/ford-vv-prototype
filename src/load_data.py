"""Load sample API records into SQLite and report coverage gaps."""

import json
import sqlite3
from pathlib import Path
from urllib.request import urlopen

from .data_quality import validate_data

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_DIR / "vv.db"
API_URL = "http://127.0.0.1:8000"


def fetch_records(base_url, endpoint):
    with urlopen(base_url.rstrip("/") + endpoint, timeout=10) as response:
        return json.load(response)


def create_tables(connection):
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS requirements (
            requirement_id TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            release TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tests (
            test_id TEXT PRIMARY KEY NOT NULL,
            requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id),
            title TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS defects (
            defect_id TEXT PRIMARY KEY NOT NULL,
            test_id TEXT NOT NULL REFERENCES tests(test_id),
            title TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tests_requirement_id
            ON tests(requirement_id);
        CREATE TABLE IF NOT EXISTS sync_metadata (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            loaded_at TEXT NOT NULL
        );
    """)


def load_snapshot(connection, requirements, tests, defects):
    # Commit all three loads together, or roll back if any record fails.
    with connection:
        # Delete children first; insert parents first to preserve valid links.
        connection.execute("DELETE FROM defects")
        connection.execute("DELETE FROM tests")
        connection.execute("DELETE FROM requirements")
        connection.executemany("""
            INSERT INTO requirements (requirement_id, title, release)
            VALUES (:requirement_id, :title, :release)
        """, requirements)
        connection.executemany("""
            INSERT INTO tests (test_id, requirement_id, title, status)
            VALUES (:test_id, :requirement_id, :title, :status)
        """, tests)
        connection.executemany("""
            INSERT INTO defects (defect_id, test_id, title, severity, status)
            VALUES (:defect_id, :test_id, :title, :severity, :status)
        """, defects)
        connection.execute("""
            INSERT OR REPLACE INTO sync_metadata (id, loaded_at)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        """)


def find_uncovered_requirements(connection):
    return connection.execute("""
        SELECT r.requirement_id, r.title
        FROM requirements r
        LEFT JOIN tests t ON r.requirement_id = t.requirement_id
        WHERE t.test_id IS NULL
        ORDER BY r.requirement_id
    """).fetchall()


def main(api_url=API_URL):
    try:
        requirements = fetch_records(api_url, "/jama/requirements")
        tests = fetch_records(api_url, "/testrail/tests")
        defects = fetch_records(api_url, "/jira/defects")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Could not read source data: {error}")
        print("Database not changed.")
        return 1

    errors = validate_data(requirements, tests, defects)
    if errors:
        print(f"Data quality check failed: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        print("Database not changed.")
        return 1

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        create_tables(connection)
        load_snapshot(connection, requirements, tests, defects)
        print(f"Loaded {len(requirements)} requirements, {len(tests)} tests, "
              f"and {len(defects)} defects into {DATABASE_PATH.name}.")
        uncovered = find_uncovered_requirements(connection)
        print(f"\nRequirements without tests: {len(uncovered)}")
        for requirement_id, title in uncovered:
            print(f"{requirement_id}: {title}")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
