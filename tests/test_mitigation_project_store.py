"""Unit tests for the session-scoped mitigation project store."""
import unittest

from src.mitigation_project_store import get_project, list_projects, save_project


class MitigationProjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.session = {}

    def test_create_and_list_multiple_independent_projects(self):
        first = save_project(self.session, {"studio_payload": {"project_name": "Pilot A"}})
        second = save_project(self.session, {"studio_payload": {"project_name": "Pilot B"}})

        self.assertNotEqual(first["project_id"], second["project_id"])
        self.assertEqual(len(list_projects(self.session)), 2)
        self.assertEqual(
            get_project(self.session, first["project_id"])["studio_payload"]["project_name"],
            "Pilot A",
        )
        self.assertEqual(
            get_project(self.session, second["project_id"])["studio_payload"]["project_name"],
            "Pilot B",
        )

    def test_update_increments_revision_and_preserves_created_at(self):
        first = save_project(self.session, {"studio_payload": {"project_name": "Pilot A"}})
        updated = save_project(
            self.session,
            {"studio_payload": {"project_name": "Pilot A revised"}},
            project_id=first["project_id"],
            expected_revision=first["revision"],
        )

        self.assertEqual(updated["project_id"], first["project_id"])
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["created_at"], first["created_at"])
        self.assertEqual(
            get_project(self.session, first["project_id"])["studio_payload"]["project_name"],
            "Pilot A revised",
        )

    def test_stale_revision_is_rejected(self):
        first = save_project(self.session, {"studio_payload": {"project_name": "Pilot A"}})
        save_project(
            self.session,
            {"studio_payload": {"project_name": "Pilot A updated"}},
            project_id=first["project_id"],
            expected_revision=1,
        )
        with self.assertRaisesRegex(ValueError, "changed after it was opened"):
            save_project(
                self.session,
                {"studio_payload": {"project_name": "stale overwrite"}},
                project_id=first["project_id"],
                expected_revision=1,
            )

    def test_missing_project_cannot_be_silently_recreated(self):
        with self.assertRaisesRegex(ValueError, "no longer in the session store"):
            save_project(
                self.session,
                {"studio_payload": {}},
                project_id="missing-project",
                expected_revision=1,
            )


if __name__ == "__main__":
    unittest.main()
