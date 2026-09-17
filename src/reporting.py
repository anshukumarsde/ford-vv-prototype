"""Read-only release report with explicit demo gates and metric definitions."""

import sqlite3

from .data_quality import validate_data


def build_report(database_path, release=None):
    connection = sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN")  # All dashboard queries see one snapshot.
        requirements = [dict(row) for row in connection.execute("SELECT * FROM requirements")]
        tests = [dict(row) for row in connection.execute("SELECT * FROM tests")]
        defects = [dict(row) for row in connection.execute("SELECT * FROM defects")]
        has_metadata = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'sync_metadata'"
        ).fetchone()
        metadata = connection.execute("SELECT loaded_at FROM sync_metadata WHERE id=1").fetchone() if has_metadata else None
        trace = [dict(row) for row in connection.execute("""
            SELECT r.release, r.requirement_id, r.title AS requirement_title,
                   t.test_id, t.title AS test_title, t.status AS test_status,
                   d.defect_id, d.severity, d.status AS defect_status
            FROM requirements r
            LEFT JOIN tests t ON t.requirement_id = r.requirement_id
            LEFT JOIN defects d ON d.test_id = t.test_id
            WHERE (? IS NULL OR r.release = ?)
            ORDER BY r.requirement_id, t.test_id, d.defect_id
        """, (release, release))]
    finally:
        connection.close()

    quality = validate_data(requirements, tests, defects)
    releases = sorted({r["release"] for r in requirements})
    requirements = [r for r in requirements if release is None or r["release"] == release]
    ids = {r["requirement_id"] for r in requirements}
    tests = [t for t in tests if t["requirement_id"] in ids]
    test_ids = {t["test_id"] for t in tests}
    defects = [d for d in defects if d["test_id"] in test_ids]
    counts = {status: sum(t["status"] == status for t in tests)
              for status in ("PASS", "FAIL", "BLOCKED", "NOT_RUN")}
    covered = {t["requirement_id"] for t in tests}
    missing = [r for r in requirements if r["requirement_id"] not in covered]
    unsuccessful = [t for t in tests if t["status"] != "PASS"]
    open_defects = [d for d in defects if d["status"] != "CLOSED"]
    critical = [d for d in open_defects if d["severity"] in ("HIGH", "CRITICAL")]
    unknown_severity = [d for d in defects if d["severity"] not in ("LOW", "MEDIUM", "HIGH", "CRITICAL")]
    loaded_at = metadata["loaded_at"] if metadata else None
    gates = [
        {"name": "Requirements and tests exist", "passed": bool(requirements and tests),
         "detail": f"{len(requirements)} requirements and {len(tests)} planned tests"},
        {"name": "All requirements have linked tests", "passed": not missing,
         "detail": f"{len(missing)} uncovered requirements"},
        {"name": "Every planned test passed", "passed": bool(tests) and not unsuccessful,
         "detail": f"{counts['FAIL']} failed, {counts['BLOCKED']} blocked, {counts['NOT_RUN']} not run"},
        {"name": "No open high or critical defects", "passed": not critical,
         "detail": f"{len(critical)} blockers including defects in progress"},
        {"name": "Snapshot data quality passes", "passed": not quality and not unknown_severity,
         "detail": f"{len(quality)} snapshot issues; {len(unknown_severity)} unknown severities in scope"},
    ]
    executed = counts["PASS"] + counts["FAIL"]
    def percent(numerator, denominator):
        return round(100 * numerator / denominator, 1) if denominator else None

    return {"release": release or "All releases", "releases": releases,
            "loaded_at": loaded_at, "ready": all(g["passed"] for g in gates), "gates": gates,
            "metrics": {"requirements": len(requirements), "tests": len(tests),
                        "covered": len(covered), "coverage": percent(len(covered), len(requirements)),
                        "executed": executed, "execution": percent(executed, len(tests)),
                        "pass_rate": percent(counts["PASS"], executed), "open_defects": len(open_defects)},
            "statuses": counts, "uncovered": missing, "attention_tests": unsuccessful,
            "open_defects": open_defects, "quality_issues": quality, "traceability": trace}
