"""Load the sample JSON files into SQLite and report coverage gaps."""

import json
import sqlite3
from pathlib import Path

from data_quality import validate_data

PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / "vv.db"


def read_records(filename):
    with (PROJECT_DIR / "data" / filename).open(encoding="utf-8") as source:
        return json.load(source)


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


def find_uncovered_requirements(connection):
    return connection.execute("""
        SELECT r.requirement_id, r.title
        FROM requirements r
        LEFT JOIN tests t ON r.requirement_id = t.requirement_id
        WHERE t.test_id IS NULL
        ORDER BY r.requirement_id
    """).fetchall()


def main():
    requirements = read_records("requirements.json")
    tests = read_records("tests.json")
    defects = read_records("defects.json")

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
