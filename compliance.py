import sqlite3


def find_missing_tests(connection):
    cursor = connection.cursor()

    query = """
        SELECT
            r.requirement_id,
            r.title
        FROM requirements r
        LEFT JOIN tests t
            ON r.requirement_id = t.requirement_id
        WHERE t.test_id IS NULL
    """

    cursor.execute(query)
    return cursor.fetchall()


def find_failed_tests(connection):
    cursor = connection.cursor()

    query = """
        SELECT
            test_id,
            name,
            status
        FROM tests
        WHERE status = 'FAIL'
    """

    cursor.execute(query)
    return cursor.fetchall()


def find_open_high_defects(connection):
    cursor = connection.cursor()

    query = """
        SELECT
            defect_id,
            summary,
            severity,
            status
        FROM defects
        WHERE severity = 'HIGH'
        AND status = 'OPEN'
    """

    cursor.execute(query)
    return cursor.fetchall()


def main():
    connection = sqlite3.connect("vv.db")

    missing_tests = find_missing_tests(connection)
    failed_tests = find_failed_tests(connection)
    high_defects = find_open_high_defects(connection)

    print("\n=== V&V COMPLIANCE REPORT ===")

    print("\nRequirements without tests:")
    for row in missing_tests:
        print(row)

    print("\nFailed tests:")
    for row in failed_tests:
        print(row)

    print("\nOpen high-severity defects:")
    for row in high_defects:
        print(row)

    connection.close()


if __name__ == "__main__":
    main()