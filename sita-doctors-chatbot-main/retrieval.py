import json
import math
import os
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


FALLBACK_MESSAGE = "Currently, Sita AI is expanding its services. We will get back to you soon."
KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parent / "knowledge_base" / "faqs.json"
DEFAULT_MATCH_THRESHOLD = 0.32
DEFAULT_MINIMUM_MARGIN = 0.10

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TOKEN_ALIASES = {
    "appt": "appointment",
    "appointments": "appointment",
    "appointments": "appointment",
    "appointments": "appointment",
    "bookings": "booking",
    "cancelled": "cancel",
    "canceled": "cancel",
    "consult": "consultation",
    "consultations": "consultation",
    "docs": "doctor",
    "doctors": "doctor",
    "fees": "fee",
    "hospitals": "hospital",
    "offline": "clinic",
    "online": "telemedicine",
    "update": "change",
    "updated": "change",
    "payouts": "payout",
    "physician": "doctor",
    "physicians": "doctor",
    "prices": "fee",
    "pricing": "fee",
    "slots": "slot",
    "telehealth": "telemedicine",
    "video": "call",
}
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "do", "does", "for",
    "from", "how", "i", "if", "in", "is", "it", "me", "my", "of", "on",
    "or", "should", "the", "to", "what", "when", "where", "which", "why",
    "with", "would", "t", "don", "doesn", "isn", "aren", "wasn", "weren",
    "won", "wouldn", "couldn", "shouldn", "haven", "hasn", "hadn",
}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    tokens = _TOKEN_RE.findall(normalized.casefold())
    return " ".join(_TOKEN_ALIASES.get(token, token) for token in tokens)


def tokenize(value: str) -> list[str]:
    return [token for token in normalize_text(value).split() if token not in _STOP_WORDS]


def _correct_spelling(tokens: list[str], vocabulary: set[str]) -> list[str]:
    corrected = []
    for token in tokens:
        if token in vocabulary or len(token) < 5:
            corrected.append(token)
            continue
        candidates = sorted(
            ((SequenceMatcher(None, token, candidate).ratio(), candidate) for candidate in vocabulary),
            reverse=True,
        )
        if candidates and candidates[0][0] >= 0.84 and (
            len(candidates) == 1 or candidates[0][0] - candidates[1][0] >= 0.06
        ):
            corrected.append(candidates[0][1])
        else:
            corrected.append(token)
    return corrected


def load_faqs(path: Path = KNOWLEDGE_BASE_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as knowledge_file:
        faqs: Any = json.load(knowledge_file)

    if not isinstance(faqs, list) or not faqs:
        raise ValueError("The FAQ knowledge base must be a non-empty JSON array.")

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    for index, faq in enumerate(faqs):
        if not isinstance(faq, dict):
            raise ValueError(f"FAQ record {index + 1} must be a JSON object.")
        faq_id, question, answer = faq.get("id"), faq.get("question"), faq.get("answer")
        if not all(isinstance(value, str) and value.strip() for value in (faq_id, question, answer)):
            raise ValueError(f"FAQ record {index + 1} must have non-empty id, question, and answer strings.")
        normalized_question = normalize_text(question)
        if faq_id in seen_ids or normalized_question in seen_questions:
            raise ValueError(f"FAQ record {index + 1} duplicates an id or question.")
        seen_ids.add(faq_id)
        seen_questions.add(normalized_question)
    return faqs


def _cosine_similarity(left: Counter[str], right: Counter[str], idf: dict[str, float]) -> float:
    dot = sum(left[token] * right.get(token, 0) * idf[token] ** 2 for token in left)
    left_norm = math.sqrt(sum(count**2 * idf[token] ** 2 for token, count in left.items()))
    right_norm = math.sqrt(sum(count**2 * idf[token] ** 2 for token, count in right.items()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _score(query: str, candidate: str, document_frequencies: Counter[str], document_count: int) -> float:
    query_tokens = Counter(tokenize(query))
    candidate_tokens = Counter(tokenize(candidate))
    vocabulary = query_tokens.keys() | candidate_tokens.keys()
    idf = {
        token: math.log(1 + (document_count + 1) / (document_frequencies[token] + 1)) + 1
        for token in vocabulary
    }
    cosine = _cosine_similarity(query_tokens, candidate_tokens, idf)
    query_normalized = normalize_text(query)
    candidate_normalized = normalize_text(candidate)
    char_similarity = SequenceMatcher(None, query_normalized, candidate_normalized).ratio()

    if query_normalized == candidate_normalized:
        return 1.0
    return 0.82 * cosine + 0.18 * char_similarity


def find_answer(
    question: str,
    faqs: list[dict[str, str]],
    threshold: float | None = None,
    minimum_margin: float = DEFAULT_MINIMUM_MARGIN,
) -> dict[str, Any] | None:
    if not isinstance(question, str) or not question.strip() or not faqs:
        return None

    match_threshold = threshold
    if match_threshold is None:
        match_threshold = float(os.environ.get("SITA_MATCH_THRESHOLD", DEFAULT_MATCH_THRESHOLD))
    if not 0 <= match_threshold <= 1:
        raise ValueError("SITA_MATCH_THRESHOLD must be between 0 and 1.")
    if not 0 <= minimum_margin <= 1:
        raise ValueError("minimum_margin must be between 0 and 1.")

    document_tokens = [set(tokenize(faq["question"])) for faq in faqs]
    document_frequencies: Counter[str] = Counter(
        token for tokens in document_tokens for token in tokens
    )
    vocabulary = set(document_frequencies)
    normalized_query_tokens = _correct_spelling(tokenize(question), vocabulary)
    normalized_query = " ".join(normalized_query_tokens)
    for faq in faqs:
        if normalized_query == " ".join(tokenize(faq["question"])):
            return {"faq": faq, "score": 1.0}

    ranked = sorted(
        (
            (
                _score(normalized_query, faq["question"], document_frequencies, len(faqs)),
                index,
                faq,
            )
            for index, faq in enumerate(faqs)
        ),
        key=lambda result: result[0],
        reverse=True,
    )

    best_score, best_index, best_faq = ranked[0]
    next_score = ranked[1][0] if len(ranked) > 1 else 0.0
    shared_terms = set(normalized_query_tokens) & document_tokens[best_index]
    if (
        best_score < match_threshold
        or best_score - next_score < minimum_margin
        or len(shared_terms) < 2
    ):
        return None
    return {"faq": best_faq, "score": best_score}
