# Sita AI — Doctor FAQ Backend

Sita AI is a standalone HTTP API that answers doctor-support questions using the approved FAQ content stored in [`knowledge_base/faqs.json`](./knowledge_base/faqs.json). Answers come only from that file; no external AI or medical-information service is used.

The API exposes `POST /api/chat` for questions and `GET /api/health` for health checks. Standalone greetings and common polite messages receive concise replies from `CONVERSATIONAL_RESPONSES` in `greetings.py`. For other messages, the backend matches the question against the approved FAQs and streams the answer as word-sized server-sent events. Unmatched questions and unavailable knowledge bases stream the configured fallback message.

## Requirements

- Python 3.10 or newer
- No third-party Python packages

## Run locally

From the project directory:

```powershell
python server.py
```

The API is available at <http://127.0.0.1:8000>. Stop the server with `Ctrl+C`. If port 8000 is occupied, set `SITA_PORT` to another available local port before starting.

For example, in PowerShell:

```powershell
$env:SITA_PORT = "8001"
python server.py
```

## Ask a question through the API

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/chat `
  -Method Post -ContentType 'application/json' `
  -Body '{"question":"How can I update my clinic address?"}'
```

The stream carries the answer from the matched FAQ. If there is no sufficiently confident, unambiguous match, it streams:

> Currently, Sita AI is expanding its services. We will get back to you soon.

The default minimum similarity score is `0.32`; set `SITA_MATCH_THRESHOLD` to a number from `0` to `1` to tune it. Ambiguous matches are rejected unless the best match exceeds the next-best match by at least `0.10`. The FAQ is validated at startup. If it cannot be loaded, the API remains available and FAQ questions receive the required fallback.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Project layout

- `server.py` — HTTP API backend
- `retrieval.py` — FAQ validation, normalization, ranking, and conservative fallback
- `greetings.py` — greeting-only conversation responses
- `formatting.py` — deterministic, source-preserving bullet-point formatting
- `knowledge_base/faqs.json` — approved question-and-answer records
- `tests/` — knowledge-base, retrieval, formatting, and streaming tests
