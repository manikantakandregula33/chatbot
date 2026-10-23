import re
import unicodedata


CONVERSATIONAL_RESPONSES = {
    "hi": "Hi! How can I help you today?",
    "hi there": "Hi! How can I help you today?",
    "hello": "Hello! How can I assist you today?",
    "hello there": "Hello! How can I assist you today?",
    "hey": "Hey! What can I help you with today?",
    "hey there": "Hey! What can I help you with today?",
    "good morning": "Good morning! How may I assist you today?",
    "good morning doctor": "Good morning! How may I assist you today?",
    "good morning sita": "Good morning! How may I assist you today?",
    "good morning sita ai": "Good morning! How may I assist you today?",
    "good afternoon": "Good afternoon! How may I help you today?",
    "good afternoon doctor": "Good afternoon! How may I help you today?",
    "good afternoon sita": "Good afternoon! How may I help you today?",
    "good afternoon sita ai": "Good afternoon! How may I help you today?",
    "good evening": "Good evening! How can I assist you today?",
    "good evening doctor": "Good evening! How can I assist you today?",
    "good evening sita": "Good evening! How can I assist you today?",
    "good evening sita ai": "Good evening! How can I assist you today?",
    "hi sita ai": "Hi! I'm here to help. What would you like to know?",
    "hello sita ai": "Hello! How can I help you today?",
    "hey sita ai": "Hey! What can I help you with today?",
    "thanks": "You're welcome!",
    "thank you": "You're welcome! I'm happy to help.",
    "thank you so much": "You're most welcome!",
    "okay": "Okay!",
    "ok": "Okay!",
    "bye": "Goodbye! Have a great day.",
    "how are you": "I'm doing well, thank you! How can I help you today?",
    "how are you doing": "I'm doing well, thank you! How can I help you today?",
    "what is your name": "I'm Sita AI, your doctor FAQ assistant.",
}
_NORMALIZED_ALIASES = {"o k": "ok"}


def normalize_message(message: str) -> str:
    normalized = unicodedata.normalize("NFKC", message).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def get_greeting_response(message: str) -> str | None:
    normalized = normalize_message(message)
    return CONVERSATIONAL_RESPONSES.get(_NORMALIZED_ALIASES.get(normalized, normalized))
