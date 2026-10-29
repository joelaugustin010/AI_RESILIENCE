"""Tests for the Phase 2 source-grounded disaster assistant."""
import json
import tempfile
import unittest
from pathlib import Path

from src.disaster_assistant import KnowledgeBaseError, answer_question, load_knowledge


class DisasterAssistantTests(unittest.TestCase):
    def test_knowledge_base_has_unique_topics_and_https_sources(self):
        topics = load_knowledge()
        self.assertGreaterEqual(len(topics), 4)
        self.assertEqual(len({topic["id"] for topic in topics}), len(topics))
        self.assertTrue(all(source["url"].startswith("https://") for topic in topics for source in topic["sources"]))

    def test_flood_question_returns_limitations_and_sources(self):
        result = answer_question("How should we prepare for urban flooding?")
        self.assertTrue(result["matched"])
        flood = next(topic for topic in result["topics"] if topic["id"] == "flood")
        self.assertTrue(flood["limitations"])
        self.assertTrue(flood["sources"])
        self.assertIn("not a live warning", result["message"])

    def test_air_quality_question_does_not_claim_factory_causation(self):
        result = answer_question("Which factory caused this air pollution?")
        self.assertTrue(result["matched"])
        topic = next(topic for topic in result["topics"] if topic["id"] == "air_quality")
        self.assertTrue(any("does not by itself identify" in topic["summary"] for _ in [0]))

    def test_unknown_question_returns_no_invented_answer(self):
        result = answer_question("Tell me the exact winning lottery numbers")
        self.assertFalse(result["matched"])
        self.assertEqual(result["topics"], [])

    def test_empty_question_prompts_for_input(self):
        result = answer_question("   ")
        self.assertFalse(result["matched"])
        self.assertIn("Enter", result["message"])

    def test_duplicate_topic_ids_are_rejected(self):
        topics = load_knowledge()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "knowledge.json"
            topics[1]["id"] = topics[0]["id"]
            path.write_text(json.dumps({"topics": topics}), encoding="utf-8")
            with self.assertRaises(KnowledgeBaseError):
                load_knowledge(path)


if __name__ == "__main__":
    unittest.main()
