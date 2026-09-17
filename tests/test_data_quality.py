"""Small checks for validation and the loader's stop-before-write behavior."""

import unittest
from unittest.mock import patch

from src import api, load_data
from src.data_quality import validate_data


class DataQualityTests(unittest.TestCase):
    """Verify validation rules and protection of the existing database."""

    def setUp(self):
        # Each test gets fresh lists because several tests intentionally mutate them.
        self.requirements = api.read_records("requirements.json")
        self.tests = api.read_records("tests.json")
        self.defects = api.read_records("defects.json")

    def validate(self):
        """Run the validator against the current test records."""
        return validate_data(self.requirements, self.tests, self.defects)

    def test_valid_samples_allow_failed_unrun_and_uncovered_tests(self):
        # Business risks are valid records; they belong in reports, not parse errors.
        self.assertEqual(self.validate(), [])

    def test_reports_multiple_problems_together(self):
        # Introduce unrelated errors and confirm they are reported in one pass.
        self.requirements.append(dict(self.requirements[0]))
        self.tests[0]["test_id"] = " "
        self.tests[0]["status"] = "Passed"
        self.tests[1]["requirement_id"] = "REQ-MISSING"
        self.defects[0]["test_id"] = "TEST-MISSING"
        self.defects[0]["status"] = "DONE"
        errors = "\n".join(self.validate())
        for expected in (
            "duplicate requirement_id", "test_id must be a nonblank string",
            "invalid status 'Passed'", "unknown requirement_id 'REQ-MISSING'",
            "unknown test_id 'TEST-MISSING'", "invalid status 'DONE'",
        ):
            self.assertIn(expected, errors)

    def test_duplicate_ids_in_each_entity(self):
        # IDs must be unique within requirements, tests, and defects.
        for records in (self.requirements, self.tests, self.defects):
            records.append(dict(records[0]))
        self.assertEqual(len(self.validate()), 3)

    def test_malformed_shapes_and_fields_report_errors(self):
        # Exercise wrong collection shapes, row shapes, types, and missing fields.
        self.assertTrue(validate_data({}, [], []))
        self.assertTrue(validate_data([None], [], []))
        for invalid in (None, "", "   ", 123, [], {}):
            with self.subTest(invalid=invalid):
                self.tests[0]["status"] = invalid
                self.assertTrue(self.validate())
        del self.requirements[0]["title"]
        self.assertIn("title must be a nonblank string", "\n".join(self.validate()))

    def test_invalid_input_never_opens_database(self):
        # Mock the API responses and prove validation stops before sqlite3.connect.
        self.tests[0]["status"] = "INVALID"
        with patch.object(load_data, "fetch_records", side_effect=[
            self.requirements, self.tests, self.defects,
        ]), patch.object(load_data.sqlite3, "connect") as connect, \
                patch("builtins.print"):
            self.assertEqual(load_data.main(), 1)
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
