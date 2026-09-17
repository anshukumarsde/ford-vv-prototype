"""Small vendor-shaped responses, generated from our fictional sample files."""

from urllib.parse import parse_qs, urlsplit


def mock_response(url, read_records):
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    if parsed.path == "/mock/jama/rest/v1/items":
        records = [{"id": i, "documentKey": row["requirement_id"],
                    "fields": {"name": row["title"], "release_demo": row["release"]}}
                   for i, row in enumerate(read_records("requirements.json"), 1)]
        start = int(query.get("startAt", [0])[0])
        limit = int(query.get("maxResults", [2])[0])
        kind = "jama"
    elif parsed.path == "/mock/testrail/index.php" and parsed.query.split("&")[0] == "/api/v2/get_tests/1":
        statuses = {"PASS": 1, "BLOCKED": 2, "NOT_RUN": 3, "FAIL": 5}
        records = [{"id": i, "case_id": i, "run_id": 1, "title": row["title"],
                    "refs": row["requirement_id"], "status_id": statuses[row["status"]],
                    "custom_source_id": row["test_id"]}
                   for i, row in enumerate(read_records("tests.json"), 1)]
        start = int(query.get("offset", [0])[0])
        limit = int(query.get("limit", [2])[0])
        kind = "testrail"
    elif parsed.path == "/mock/jira/rest/api/3/search/jql":
        statuses = {"OPEN": "To Do", "IN_PROGRESS": "In Progress", "CLOSED": "Done"}
        records = [{"id": str(i), "key": row["defect_id"], "fields": {
            "summary": row["title"], "status": {"name": statuses[row["status"]]},
            "priority": {"name": row["severity"].title()},
            "customfield_10001": row["test_id"]}}
            for i, row in enumerate(read_records("defects.json"), 1)]
        start = int(query.get("nextPageToken", [0])[0])
        limit = int(query.get("maxResults", [2])[0])
        kind = "jira"
    else:
        return None

    if start < 0 or not 1 <= limit <= 100:
        raise ValueError("Invalid page bounds")
    page = records[start:start + limit]
    more = start + limit < len(records)
    if kind == "jama":
        return {"data": page, "meta": {"pageInfo": {
            "startIndex": start, "resultCount": len(page), "totalResults": len(records)}}}
    if kind == "testrail":
        next_link = f"/api/v2/get_tests/1&offset={start + limit}&limit={limit}" if more else None
        return {"tests": page, "offset": start, "limit": limit, "size": len(page),
                "_links": {"next": next_link, "prev": None}}
    result = {"issues": page, "isLast": not more}
    if more:
        result["nextPageToken"] = str(start + limit)
    return result
