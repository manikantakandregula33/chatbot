import unittest

from formatting import format_answer_for_display
from retrieval import FALLBACK_MESSAGE


class AnswerFormattingTests(unittest.TestCase):
    def test_multi_action_answer_becomes_bullet_steps_without_new_content(self) -> None:
        answer = (
            "Go to Clinic Location in the sidebar, update the address text and Google Maps "
            "share link, and click Save Clinic Details."
        )
        formatted = format_answer_for_display(answer)

        self.assertTrue(formatted.startswith("**Steps to follow**\n\n"))
        self.assertIn("- Go to Clinic Location in the sidebar.", formatted)
        self.assertIn("- Update the address text", formatted)
        self.assertIn("- Click Save Clinic Details.", formatted)
        self.assertNotIn("1.", formatted)
        self.assertNotIn("upload", formatted.casefold())

    def test_multiple_action_sentences_are_bulleted_in_source_order(self) -> None:
        answer = (
            "Check that your device's audio output is working. Confirm that the call is not muted. "
            "If the problem continues, reconnect if possible and contact support."
        )
        formatted = format_answer_for_display(answer)

        self.assertIn("- Check that your device's audio output is working.", formatted)
        self.assertIn("- Confirm that the call is not muted.", formatted)
        self.assertLess(formatted.index("reconnect"), formatted.index("contact support"))

    def test_simple_factual_answer_remains_concise(self) -> None:
        answer = "The follow-up fee is a discounted rate for return visits within a treatment cycle."
        self.assertEqual(format_answer_for_display(answer), answer)

    def test_existing_fact_list_is_rendered_as_bullets(self) -> None:
        answer = (
            "You can update your mobile number, state and district, doctor type and primary specialty, "
            "years of experience, ABDM Healthcare Professional ID (HPR ID), and medical system. "
            "Verified medical credentials remain locked after approval."
        )
        formatted = format_answer_for_display(answer)

        self.assertIn("- mobile number", formatted)
        self.assertIn("- state and district", formatted)
        self.assertIn("- doctor type and primary specialty", formatted)
        self.assertIn("- medical system", formatted)
        self.assertIn("Verified medical credentials remain locked after approval.", formatted)

    def test_fallback_is_not_changed_by_display_formatter(self) -> None:
        self.assertEqual(format_answer_for_display(FALLBACK_MESSAGE), FALLBACK_MESSAGE)


if __name__ == "__main__":
    unittest.main()
