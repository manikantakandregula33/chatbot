import json
import unittest
from pathlib import Path
from unittest.mock import patch

from retrieval import (
    DEFAULT_MATCH_THRESHOLD,
    FALLBACK_MESSAGE,
    find_answer,
    load_faqs,
    normalize_text,
)


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeBaseTests(unittest.TestCase):
    def test_knowledge_base_is_valid_and_contains_all_35_source_faqs(self) -> None:
        faqs = load_faqs(ROOT / "knowledge_base" / "faqs.json")
        self.assertEqual(len(faqs), 35)
        self.assertEqual(len({faq["id"] for faq in faqs}), 35)
        self.assertTrue(all(faq["question"] and faq["answer"] for faq in faqs))

    def test_invalid_knowledge_base_is_rejected(self) -> None:
        path = ROOT / "knowledge_base" / "invalid-test-data.json"
        path.write_text(json.dumps([{"id": "x", "question": "Question"}]), encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                load_faqs(path)
        finally:
            path.unlink()


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.faqs = load_faqs(ROOT / "knowledge_base" / "faqs.json")

    def assert_answer_matches(self, question: str, faq_id: str) -> None:
        result = find_answer(question, self.faqs)
        self.assertIsNotNone(result, question)
        self.assertEqual(result["faq"]["id"], faq_id)
        self.assertEqual(result["faq"]["answer"], next(faq["answer"] for faq in self.faqs if faq["id"] == faq_id))

    def test_exact_and_case_insensitive_matches(self) -> None:
        self.assert_answer_matches(self.faqs[2]["question"], "faq-03")
        self.assert_answer_matches("HOW DO I CHANGE MY CLINIC ADDRESS?", "faq-03")

    def test_natural_language_and_spelling_variants(self) -> None:
        self.assert_answer_matches("How can I update my clinic adress?", "faq-03")
        self.assert_answer_matches("Where do I see if the patient has paid?", "faq-19")
        self.assert_answer_matches("How do I get my consultation payout?", "faq-05")
        self.assertIsNone(find_answer("Why can't I join a telehealth video?", self.faqs))

    def test_ambiguous_and_unrelated_questions_use_fallback(self) -> None:
        self.assertIsNone(find_answer("How do I change it?", self.faqs))
        self.assertIsNone(find_answer("What about my earnings?", self.faqs))
        self.assertIsNone(find_answer("What is the weather today?", self.faqs))
        self.assertEqual(FALLBACK_MESSAGE, "Currently, Sita AI is expanding its services. We will get back to you soon.")

    def test_matching_threshold_can_be_configured(self) -> None:
        with patch.dict("os.environ", {"SITA_MATCH_THRESHOLD": "1"}):
            self.assertEqual(DEFAULT_MATCH_THRESHOLD, 0.32)
            self.assertIsNone(find_answer("Where can I check my earnings?", self.faqs))
        with self.assertRaises(ValueError):
            find_answer("hello", self.faqs, threshold=1.1)

    def test_spelling_normalization_is_case_insensitive(self) -> None:
        self.assertEqual(normalize_text("Doctor's APPT"), "doctor s appointment")
        self.assert_answer_matches("How can I update my clinic adress?", "faq-03")


if __name__ == "__main__":
    unittest.main()
