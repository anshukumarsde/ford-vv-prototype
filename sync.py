import sqlite3
import requests


BASE_URL = "http://127.0.0.1:8000"


def get_data(endpoint):
    response = requests.get(BASE_URL + endpoint)

    response.raise_for_status()

    return response.json()


def create_tables(connection):
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requirements (
            requirement_id TEXT PRIMARY KEY,
            title TEXT,
            program TEXT,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            test_id TEXT PRIMARY KEY,
            requirement_id TEXT,
            name TEXT,
            test_level TEXT,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defects (
            defect_id TEXT PRIMARY KEY,
            test_id TEXT,
            summary TEXT,
            severity TEXT,
            status TEXT
        )
    """)

    connection.commit()


def load_requirements(connection, requirements):
    cursor = connection.cursor()

    for requirement in requirements:
        cursor.execute("""
            INSERT OR REPLACE INTO requirements
            VALUES (?, ?, ?, ?)
        """, (
            requirement["requirement_id"],
            requirement["title"],
            requirement["program"],
            requirement["status"]
        ))

    connection.commit()


def load_tests(connection, tests):
    cursor = connection.cursor()

    for test in tests:
        cursor.execute("""
            INSERT OR REPLACE INTO tests
            VALUES (?, ?, ?, ?, ?)
        """, (
            test["test_id"],
            test["requirement_id"],
            test["name"],
            test["test_level"],
            test["status"]
        ))

    connection.commit()


def load_defects(connection, defects):
    cursor = connection.cursor()

    for defect in defects:
        cursor.execute("""
            INSERT OR REPLACE INTO defects
            VALUES (?, ?, ?, ?, ?)
        """, (
            defect["defect_id"],
            defect["test_id"],
            defect["summary"],
            defect["severity"],
            defect["status"]
        ))

    connection.commit()


def main():
    print("Starting V&V data sync...")

    requirements = get_data("/jama/requirements")
    tests = get_data("/testrail/tests")
    defects = get_data("/jira/defects")

    connection = sqlite3.connect("vv.db")

    create_tables(connection)

    load_requirements(connection, requirements)
    load_tests(connection, tests)
    load_defects(connection, defects)

    connection.close()

    print("V&V data sync completed successfully.")


if __name__ == "__main__":
    main()