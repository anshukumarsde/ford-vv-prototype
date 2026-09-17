"""Translate the local vendor mocks into the shared reporting schema."""

from urllib.parse import quote


def fetch_vendor_data(base_url, fetch):
    requirements, tests, defects = [], [], []
    endpoint = "/mock/jama/rest/v1/items?startAt=0&maxResults=2"
    seen = set()
    while endpoint:
        if endpoint in seen:
            raise ValueError("Jama pagination did not advance")
        seen.add(endpoint)
        page = fetch(base_url, endpoint)
        for row in page["data"]:
            requirements.append({"requirement_id": row["documentKey"],
                                 "title": row["fields"]["name"],
                                 "release": row["fields"]["release_demo"]})
        info = page["meta"]["pageInfo"]
        next_start = info["startIndex"] + info["resultCount"]
        endpoint = (f"/mock/jama/rest/v1/items?startAt={next_start}&maxResults=2"
                    if next_start < info["totalResults"] else None)

    endpoint = "/mock/testrail/index.php?/api/v2/get_tests/1&offset=0&limit=2"
    seen = set()
    statuses = {1: "PASS", 2: "BLOCKED", 3: "NOT_RUN", 5: "FAIL"}
    while endpoint:
        if endpoint in seen:
            raise ValueError("TestRail pagination did not advance")
        seen.add(endpoint)
        page = fetch(base_url, endpoint)
        for row in page["tests"]:
            if row["status_id"] not in statuses:
                raise ValueError(f"Unsupported TestRail status ID: {row['status_id']}")
            if "," in row["refs"]:
                raise ValueError("This demo supports one requirement reference per test")
            tests.append({"test_id": row["custom_source_id"], "title": row["title"],
                          "requirement_id": row["refs"], "status": statuses[row["status_id"]]})
        link = page["_links"]["next"]
        if link and not link.startswith("/api/v2/get_tests/1&"):
            raise ValueError("Unexpected TestRail pagination link")
        endpoint = "/mock/testrail/index.php?" + link if link else None

    endpoint = "/mock/jira/rest/api/3/search/jql?maxResults=2"
    seen = set()
    statuses = {"To Do": "OPEN", "In Progress": "IN_PROGRESS", "Done": "CLOSED"}
    while endpoint:
        if endpoint in seen:
            raise ValueError("Jira pagination did not advance")
        seen.add(endpoint)
        page = fetch(base_url, endpoint)
        for row in page["issues"]:
            fields = row["fields"]
            if fields["status"]["name"] not in statuses:
                raise ValueError(f"Unmapped Jira status: {fields['status']['name']}")
            defects.append({"defect_id": row["key"], "title": fields["summary"],
                            "test_id": fields["customfield_10001"],
                            "severity": fields["priority"]["name"].upper(),
                            "status": statuses[fields["status"]["name"]]})
        endpoint = ("/mock/jira/rest/api/3/search/jql?maxResults=2&nextPageToken="
                    + quote(page["nextPageToken"], safe="") if not page["isLast"] else None)
    return requirements, tests, defects
