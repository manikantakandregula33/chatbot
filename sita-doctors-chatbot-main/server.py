
import json
import logging
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from formatting import format_answer_for_display
from greetings import get_greeting_response
from retrieval import FALLBACK_MESSAGE, find_answer, load_faqs


MAX_REQUEST_BYTES = 16_384
STREAM_WORD_PATTERN = re.compile(r"\S+\s*")

# For a public chatbot that does not use cookies or credentials,
# "*" permits requests from any frontend origin.
# For production, replace "*" with your frontend's exact origin.
ALLOWED_ORIGIN = os.environ.get("CORS_ALLOWED_ORIGIN", "*")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("sita-ai")


class SitaRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    faqs: list[dict[str, str]] | None = None
    knowledge_base_error: str | None = None

    def _add_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS, HEAD",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization",
        )
        self.send_header("Vary", "Origin")
        self.send_header("X-Content-Type-Options", "nosniff")

    def do_OPTIONS(self) -> None:
        request_path = urlparse(self.path).path

        if request_path != "/api/chat":
            self.send_error(404, "Not found")
            return

        self.send_response(204)
        self._add_cors_headers()
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:
        if urlparse(self.path).path != "/api/health":
            self.send_error(404, "Not found")
            return

        self.send_response(200)
        self._add_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        request_path = urlparse(self.path).path

        if request_path == "/api/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "knowledgeBaseLoaded": self.faqs is not None,
                },
            )
            return

        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
        except ValueError:
            self._send_json(
                400, {"error": "Invalid Content-Length header."}
            )
            return

        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            status = 413 if content_length > MAX_REQUEST_BYTES else 400
            self._send_json(
                status, {"error": "Invalid request size."}
            )
            return

        try:
            payload: Any = json.loads(
                self.rfile.read(content_length)
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(
                400, {"error": "Request body must contain valid JSON."}
            )
            return

        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("question"), str)
        ):
            self._send_json(
                400,
                {
                    "error": (
                        "Request body must contain a question string."
                    )
                },
            )
            return

        greeting = get_greeting_response(payload["question"])
        answer = greeting or FALLBACK_MESSAGE
        matched = greeting is not None

        if greeting is None:
            if self.faqs is None:
                logger.error(
                    "FAQ knowledge base unavailable: %s",
                    self.knowledge_base_error,
                )
            else:
                try:
                    match = find_answer(payload["question"], self.faqs)
                except (ValueError, OSError) as error:
                    logger.exception(
                        "Unable to match the submitted question: %s",
                        error,
                    )
                    self._send_json(
                        500,
                        {"error": "The question could not be processed."},
                    )
                    return

                if match is not None:
                    answer = format_answer_for_display(
                        match["faq"]["answer"]
                    )
                    matched = True

        self._stream_answer(answer, matched)

    def _stream_answer(self, answer: str, matched: bool) -> None:
        self.close_connection = True
        self.send_response(200)
        self._add_cors_headers()
        self.send_header(
            "Content-Type", "text/event-stream; charset=utf-8"
        )
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "close")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            for chunk in STREAM_WORD_PATTERN.findall(answer):
                self._write_sse_event("chunk", {"text": chunk})

            self._write_sse_event("done", {"matched": matched})
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()

        except (
            BrokenPipeError,
            ConnectionResetError,
            ConnectionAbortedError,
        ):
            logger.info("Chat stream disconnected by client.")

    def _write_sse_event(
        self, event: str, payload: dict[str, Any]
    ) -> None:
        event_data = (
            f"event: {event}\n"
            f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        ).encode("utf-8")

        self.wfile.write(
            f"{len(event_data):X}\r\n".encode("ascii")
        )
        self.wfile.write(event_data)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

    def _send_json(
        self, status: int, payload: dict[str, Any]
    ) -> None:
        body = json.dumps(
            payload, ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)
        self._add_cors_headers()
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(
        self, format_string: str, *args: Any
    ) -> None:
        logger.info(
            "%s - %s",
            self.address_string(),
            format_string % args,
        )


def main() -> None:
    try:
        SitaRequestHandler.faqs = load_faqs()
        SitaRequestHandler.knowledge_base_error = None
        logger.info("FAQ knowledge base loaded successfully.")

    except (OSError, json.JSONDecodeError, ValueError) as error:
        SitaRequestHandler.faqs = None
        SitaRequestHandler.knowledge_base_error = str(error)
        logger.exception("FAQ knowledge base could not be loaded")

    # Render supplies PORT; local development can use SITA_PORT.
    host = "0.0.0.0"
    port = int(
        os.environ.get(
            "PORT",
            os.environ.get("SITA_PORT", "8000"),
        )
    )

    logger.info("Sita AI is available at http://%s:%s", host, port)

    with ThreadingHTTPServer(
        (host, port), SitaRequestHandler
    ) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down Sita AI")


if __name__ == "__main__":
    main()
