"""Check sample records without modifying them or connecting to a database."""

TEST_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
DEFECT_STATUSES = {"OPEN", "IN_PROGRESS", "CLOSED"}


def check_records(records, filename, fields, errors, statuses=None):
    """Check one file and return its usable rows and unique IDs."""
    # Each source endpoint must return a JSON array, represented here as a list.
    if not isinstance(records, list):
        errors.append(f"{filename}: expected a JSON array of records")
        return [], set()

    # A set makes duplicate-ID checks fast and also supports relationship checks.
    ids = set()
    rows = []
    id_field = fields[0]
    for row_number, record in enumerate(records, start=1):
        location = f"{filename} row {row_number}"
        if not isinstance(record, dict):
            errors.append(f"{location}: expected a JSON object")
            continue
        rows.append((location, record))
        # Every field listed by the caller is required and must contain text.
        for field in fields:
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{location}: {field} must be a nonblank string")

        # The first required field is the unique ID for this type of record.
        record_id = record.get(id_field)
        if isinstance(record_id, str) and record_id.strip():
            if record_id in ids:
                errors.append(f"{location}: duplicate {id_field} {record_id!r}")
            ids.add(record_id)

        # Status validation applies only when the caller supplies allowed values.
        status = record.get("status")
        if statuses and isinstance(status, str) and status.strip():
            if status not in statuses:
                errors.append(
                    f"{location}: invalid status {status!r}; "
                    f"expected one of {', '.join(sorted(statuses))}"
                )
    return rows, ids


def validate_data(requirements, tests, defects):
    """Return all detected problems; an empty list means validation passed."""
    errors = []

    # Validate each dataset independently and collect its valid IDs.
    _, requirement_ids = check_records(
        requirements, "requirements.json",
        ("requirement_id", "title", "release"), errors,
    )
    test_rows, test_ids = check_records(
        tests, "tests.json",
        ("test_id", "requirement_id", "title", "status"), errors, TEST_STATUSES,
    )
    defect_rows, _ = check_records(
        defects, "defects.json",
        ("defect_id", "test_id", "title", "severity", "status"),
        errors, DEFECT_STATUSES,
    )

    # Validate relationships after all parent IDs have been collected.
    for rows, field, parent_ids in (
        (test_rows, "requirement_id", requirement_ids),
        (defect_rows, "test_id", test_ids),
    ):
        for location, record in rows:
            reference = record.get(field)
            if isinstance(reference, str) and reference.strip():
                if reference not in parent_ids:
                    errors.append(f"{location}: unknown {field} {reference!r}")
    return errors
