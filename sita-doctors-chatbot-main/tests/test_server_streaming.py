import json
import re
import threading
import unittest
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from greetings import CONVERSATIONAL_RESPONSES, get_greeting_response, normalize_message
from retrieval import FALLBACK_MESSAGE, load_faqs
from server import SitaRequestHandler


class StreamingEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        SitaRequestHandler.faqs = load_faqs()
        SitaRequestHandler.knowledge_base_error = None
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), SitaRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/api/chat"
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request_answer(self, question: str) -> tuple[str, list[dict[str, object]], str]:
        request = Request(
            self.url,
            data=json.dumps({"question": question}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            self.assertIn("text/event-stream", response.headers.get("Content-Type", ""))
            events = response.read().decode("utf-8").strip().split("\n\n")

        parsed_events = []
        for event in events:
            lines = event.splitlines()
            event_type = next(line[7:] for line in lines if line.startswith("event: "))
            event_data = next(line[6:] for line in lines if line.startswith("data: "))
            parsed_events.append({"type": event_type, "data": json.loads(event_data)})
        answer = "".join(
            item["data"]["text"]
            for item in parsed_events
            if item["type"] == "chunk"
        )
        return answer, parsed_events, response.headers.get("Transfer-Encoding", "")

    def test_matched_approved_answer_is_streamed_in_chunks(self) -> None:
        answer, events, transfer_encoding = self.request_answer("How do I change my clinic address?")

        self.assertGreater(sum(event["type"] == "chunk" for event in events), 1)
        self.assertEqual(transfer_encoding, "chunked")
        chunks = [
            event["data"]["text"]
            for event in events
            if event["type"] == "chunk"
        ]
        self.assertTrue(all(len(re.findall(r"\S+", chunk)) == 1 for chunk in chunks))
        self.assertTrue(answer.startswith("**Steps to follow**"))
        self.assertIn("- Click Save Clinic Details.", answer)
        self.assertNotIn("1.", answer)
        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(events[-1]["data"]["matched"])

    def test_health_endpoint_reports_loaded_knowledge_base(self) -> None:
        with urlopen(f"{self.base_url}/api/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(
                json.loads(response.read()),
                {"status": "ok", "knowledgeBaseLoaded": True},
            )

    def test_frontend_routes_are_not_served(self) -> None:
        for path in ("/", "/index.html"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                urlopen(f"{self.base_url}{path}", timeout=5)
            self.assertEqual(error.exception.code, 404)

    def test_unmatched_question_streams_exact_fallback(self) -> None:
        answer, events, _ = self.request_answer("What is the weather today?")

        self.assertEqual(answer, FALLBACK_MESSAGE)
        self.assertEqual(events[-1]["type"], "done")
        self.assertFalse(events[-1]["data"]["matched"])

    def test_all_configured_conversational_responses_stream_word_by_word(self) -> None:
        for phrase, expected_response in CONVERSATIONAL_RESPONSES.items():
            with self.subTest(phrase=phrase):
                answer, events, _ = self.request_answer(phrase)

                self.assertEqual(answer, expected_response)
                chunks = [
                    event["data"]["text"]
                    for event in events
                    if event["type"] == "chunk"
                ]
                self.assertTrue(chunks)
                self.assertTrue(all(len(re.findall(r"\S+", chunk)) == 1 for chunk in chunks))
                if len(expected_response.split()) > 1:
                    self.assertGreater(len(chunks), 1)
                self.assertTrue(events[-1]["data"]["matched"])

    def test_greeting_with_a_question_still_uses_faq_matching(self) -> None:
        answer, events, _ = self.request_answer("Hi, where can I check my earnings?")

        self.assertIn("Open Earnings", answer)
        self.assertTrue(events[-1]["data"]["matched"])

    def test_combined_greeting_and_medical_question_uses_fallback_without_fabrication(self) -> None:
        answer, events, _ = self.request_answer("Good morning, what is the product dosage?")

        self.assertEqual(answer, FALLBACK_MESSAGE)
        self.assertFalse(events[-1]["data"]["matched"])

    def test_punctuation_case_spacing_and_complete_message_detection(self) -> None:
        self.assertEqual(get_greeting_response("  hI!!! "), CONVERSATIONAL_RESPONSES["hi"])
        self.assertEqual(
            get_greeting_response("  GOOD   AFTERNOON, SITA AI!!! "),
            CONVERSATIONAL_RESPONSES["good afternoon sita ai"],
        )
        self.assertEqual(get_greeting_response("Thank you so much!!!"), CONVERSATIONAL_RESPONSES["thank you so much"])
        self.assertEqual(get_greeting_response("  O.K. "), CONVERSATIONAL_RESPONSES["ok"])
        self.assertEqual(normalize_message("How are you???"), "how are you")
        self.assertIsNone(get_greeting_response("Hi, where can I see my earnings?"))
        self.assertIsNone(get_greeting_response("This is a high priority question"))


if __name__ == "__main__":
    unittest.main()
