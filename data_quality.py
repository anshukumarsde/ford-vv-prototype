import sqlite3


VALID_REQUIREMENT_STATUSES = {"APPROVED", "DRAFT", "REJECTED"}
VALID_TEST_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
VALID_DEFECT_STATUSES = {"OPEN", "CLOSED", "IN_PROGRESS"}


def check_missing_ids(connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM requirements
        WHERE requirement_id IS NULL
        OR requirement_id = ''
    """)

    return cursor.fetchall()


def check_invalid_test_statuses(connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT test_id, status
        FROM tests
    """)

    invalid_rows = []

    for test_id, status in cursor.fetchall():
        if status not in VALID_TEST_STATUSES:
            invalid_rows.append((test_id, status))

    return invalid_rows


def check_broken_requirement_links(connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            t.test_id,
            t.requirement_id
        FROM tests t
        LEFT JOIN requirements r
            ON t.requirement_id = r.requirement_id
        WHERE r.requirement_id IS NULL
    """)

    return cursor.fetchall()


def check_duplicate_requirement_ids(connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            requirement_id,
            COUNT(*)
        FROM requirements
        GROUP BY requirement_id
        HAVING COUNT(*) > 1
    """)

    return cursor.fetchall()


def main():
    connection = sqlite3.connect("vv.db")

    missing_ids = check_missing_ids(connection)
    invalid_statuses = check_invalid_test_statuses(connection)
    broken_links = check_broken_requirement_links(connection)
    duplicates = check_duplicate_requirement_ids(connection)

    print("\n=== DATA QUALITY REPORT ===")

    print("\nMissing requirement IDs:")
    print(missing_ids)

    print("\nInvalid test statuses:")
    print(invalid_statuses)

    print("\nBroken requirement-to-test links:")
    print(broken_links)

    print("\nDuplicate requirement IDs:")
    print(duplicates)

    connection.close()


if __name__ == "__main__":
    main()