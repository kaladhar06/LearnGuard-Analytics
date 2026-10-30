
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from src import api


class TestLearnGuardAPI(unittest.TestCase):

    def test_root_endpoint(self):
        result = api.root()

        self.assertEqual(result["project"], "LearnGuard Analytics")
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["database"], "learnguard_staging")

    @patch("src.api.fetch_all")
    def test_health_endpoint(self, mock_fetch):
        mock_fetch.return_value = [
            {"database_name": "learnguard_staging"}
        ]

        result = api.health()

        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["database"], "learnguard_staging")

    @patch("src.api.fetch_all")
    def test_learner_mastery(self, mock_fetch):
        mock_fetch.side_effect = [
            [{"learner_id": "LRN-000001", "learner_status": "active"}],
            [{
                "course_id": "CRS-000001",
                "course_name": "Python Basics",
                "total_content": 4,
                "completed_content": 2,
                "course_completed": 0,
            }],
        ]

        result = api.learner_mastery("LRN-000001")

        self.assertEqual(result["learner_id"], "LRN-000001")
        self.assertEqual(len(result["courses"]), 1)
        self.assertEqual(
            result["courses"][0]["mastery_percentage"], 50.0
        )

    @patch("src.api.fetch_all")
    def test_recommendations(self, mock_fetch):
        mock_fetch.side_effect = [
            [{"learner_id": "LRN-000001"}],
            [{
                "course_id": "CRS-000001",
                "course_name": "Python Basics",
                "total_content": 4,
                "completed_content": 2,
                "is_completed": 0,
            }],
        ]

        result = api.recommendations("LRN-000001")

        self.assertEqual(result["learner_id"], "LRN-000001")
        self.assertEqual(len(result["recommendations"]), 1)
        self.assertEqual(
            result["recommendations"][0]["completed_content"], 2
        )

    @patch("src.api.fetch_all")
    def test_missing_learner_returns_404(self, mock_fetch):
        mock_fetch.return_value = []

        with self.assertRaises(HTTPException) as error:
            api.learner_mastery("INVALID-LEARNER")

        self.assertEqual(error.exception.status_code, 404)

    @patch("src.api.fetch_all")
    def test_learning_content(self, mock_fetch):
        mock_fetch.side_effect = [
            [{"enrollment_id": "ENR-001"}],
            [{
                "content_id": "CNT-001",
                "title": "Introduction",
                "content_type": "module",
                "sequence_no": 1,
                "duration_minutes": 20,
            }],
        ]

        result = api.learning_content(
            "LRN-000001", "CRS-000001"
        )

        self.assertEqual(result["content_count"], 1)
        self.assertEqual(result["content"][0]["title"], "Introduction")

    @patch("src.api.fetch_all")
    def test_learning_path_generation(self, mock_fetch):
        mock_fetch.side_effect = [
            [{"learner_id": "LRN-000001"}],
            [{
                "course_id": "CRS-000001",
                "course_name": "Python Basics",
            }],
            [{"enrollment_id": "ENR-001"}],
        ]

        request = api.LearningPathRequest(
            course_id="CRS-000001",
            goal="Complete Python",
        )

        result = api.create_learning_path(
            "LRN-000001", request
        )

        self.assertEqual(result["status"], "generated")
        self.assertEqual(result["goal"], "Complete Python")
        self.assertEqual(len(result["learning_path"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
