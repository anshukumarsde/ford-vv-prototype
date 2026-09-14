import sqlite3

import pandas as pd
import streamlit as st

import sync as data_sync


st.title("V&V Test Status Dashboard")


# -----------------------------
# Sync latest data
# -----------------------------
if st.button("Sync Latest Test Data"):
    try:
        data_sync.main()
        st.success("Data synchronized successfully.")
    except Exception as error:
        st.error(f"Data synchronization failed: {error}")


# -----------------------------
# Connect to SQLite database
# -----------------------------
connection = sqlite3.connect("vv.db")


# -----------------------------
# Load data
# -----------------------------
requirements = pd.read_sql_query(
    "SELECT * FROM requirements",
    connection
)

tests = pd.read_sql_query(
    "SELECT * FROM tests",
    connection
)

defects = pd.read_sql_query(
    "SELECT * FROM defects",
    connection
)


# -----------------------------
# Calculate KPIs
# -----------------------------
total_requirements = len(requirements)

requirements_with_tests = tests[
    "requirement_id"
].nunique()

total_tests = len(tests)

passed_tests = len(
    tests[tests["status"] == "PASS"]
)

failed_tests = len(
    tests[tests["status"] == "FAIL"]
)

open_defects = len(
    defects[defects["status"] == "OPEN"]
)


if total_tests > 0:
    pass_rate = (
        passed_tests
        / total_tests
        * 100
    )
else:
    pass_rate = 0


if total_requirements > 0:
    coverage = (
        requirements_with_tests
        / total_requirements
        * 100
    )
else:
    coverage = 0


# -----------------------------
# Display KPIs
# -----------------------------
st.subheader("Program KPIs")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Requirements",
    total_requirements
)

col2.metric(
    "Test Coverage",
    f"{coverage:.0f}%"
)

col3.metric(
    "Test Pass Rate",
    f"{pass_rate:.0f}%"
)

col4.metric(
    "Open Defects",
    open_defects
)


# -----------------------------
# Requirements table
# -----------------------------
st.subheader("Requirements")

st.dataframe(
    requirements,
    use_container_width=True
)


# -----------------------------
# Test execution table
# -----------------------------
st.subheader("Test Execution")

st.dataframe(
    tests,
    use_container_width=True
)


# -----------------------------
# Defects table
# -----------------------------
st.subheader("Defects")

st.dataframe(
    defects,
    use_container_width=True
)


# -----------------------------
# End-to-End Traceability
# -----------------------------
traceability_query = """
SELECT
    r.requirement_id,
    r.title,
    t.test_id,
    t.name AS test_name,
    t.test_level,
    t.status AS test_status,
    d.defect_id,
    d.summary AS defect_summary,
    d.severity,
    d.status AS defect_status
FROM requirements r
LEFT JOIN tests t
    ON r.requirement_id = t.requirement_id
LEFT JOIN defects d
    ON t.test_id = d.test_id
ORDER BY r.requirement_id
"""

traceability = pd.read_sql_query(
    traceability_query,
    connection
)

st.subheader("End-to-End Traceability")

st.dataframe(
    traceability,
    use_container_width=True
)


# -----------------------------
# Risk Summary
# -----------------------------
st.subheader("Risk Summary")


# Requirements without tests
missing_test_query = """
SELECT
    r.requirement_id,
    r.title
FROM requirements r
LEFT JOIN tests t
    ON r.requirement_id = t.requirement_id
WHERE t.test_id IS NULL
"""

missing_test_requirements = pd.read_sql_query(
    missing_test_query,
    connection
)


# Failed tests
failed_test_query = """
SELECT
    t.test_id,
    t.name,
    t.requirement_id,
    t.status
FROM tests t
WHERE t.status = 'FAIL'
"""

failed_test_details = pd.read_sql_query(
    failed_test_query,
    connection
)


# High-severity open defects
high_defect_query = """
SELECT
    d.defect_id,
    d.summary,
    d.severity,
    d.status,
    d.test_id
FROM defects d
WHERE d.severity = 'HIGH'
AND d.status = 'OPEN'
"""

high_defect_details = pd.read_sql_query(
    high_defect_query,
    connection
)


# Display missing coverage
st.write("Requirements Missing Test Coverage")

if len(missing_test_requirements) == 0:
    st.success(
        "No requirements are missing test coverage."
    )
else:
    st.dataframe(
        missing_test_requirements,
        use_container_width=True
    )


# Display failed tests
st.write("Failed Tests")

if len(failed_test_details) == 0:
    st.success(
        "No failed tests."
    )
else:
    st.dataframe(
        failed_test_details,
        use_container_width=True
    )


# Display high-severity defects
st.write("Open High-Severity Defects")

if len(high_defect_details) == 0:
    st.success(
        "No open high-severity defects."
    )
else:
    st.dataframe(
        high_defect_details,
        use_container_width=True
    )


# -----------------------------
# Release Readiness
# -----------------------------
st.subheader("Release Readiness")

high_defects = defects[
    (defects["severity"] == "HIGH")
    & (defects["status"] == "OPEN")
]

missing_requirements = (
    total_requirements
    - requirements_with_tests
)


if (
    failed_tests == 0
    and len(high_defects) == 0
    and missing_requirements == 0
):
    st.success(
        "READY FOR RELEASE"
    )

else:
    st.error(
        "NOT READY FOR RELEASE"
    )

    if failed_tests > 0:
        st.write(
            f"- {failed_tests} test(s) are failing."
        )

    if missing_requirements > 0:
        st.write(
            f"- {missing_requirements} requirement(s) "
            "have no test coverage."
        )

    if len(high_defects) > 0:
        st.write(
            f"- {len(high_defects)} high-severity "
            "defect(s) remain open."
        )


# -----------------------------
# Close database connection
# -----------------------------
connection.close()