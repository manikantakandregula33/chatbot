
import re


UNRELATED_MESSAGE = (
    "I'm Sita AI, an assistant for doctors using the ABP platform. "
    "I can help with ABP-related questions about your account, "
    "appointments, consultations, earnings, payouts, video calls, "
    "clinic details, and profile."
)


ABP_TERMS = {
    "abp",
    "doctor",
    "physician",
    "clinic",
    "hospital",
    "patient",
    "appointment",
    "consultation",
    "earning",
    "earnings",
    "income",
    "revenue",
    "payout",
    "payouts",
    "payment",
    "payments",
    "withdrawal",
    "withdrawals",
    "commission",
    "account",
    "profile",
    "registration",
    "verification",
    "dashboard",
    "booking",
    "bookings",
    "schedule",
    "scheduling",
    "availability",
    "slot",
    "slots",
    "video",
    "call",
    "meeting",
    "prescription",
    "medical",
    "document",
    "documents",
    "upload",
    "support",
    "login",
    "password",
    "subscription",
    "telemedicine",
    "telehealth",
    "notification",
    "notifications",
    "practice",
    "fee",
    "fees",
    "transaction",
    "transactions",
}


ABP_PHRASES = {
    "video call",
    "join call",
    "join consultation",
    "start consultation",
    "end consultation",
    "online consultation",
    "doctor account",
    "doctor profile",
    "clinic address",
    "clinic details",
    "consultation earnings",
    "consultation fees",
    "payment status",
    "payout status",
    "payment history",
    "earning history",
    "appointment booking",
    "appointment schedule",
    "patient booking",
    "profile update",
    "account verification",
    "change password",
    "forgot password",
    "login issue",
    "doctor registration",
    "upload documents",
    "update profile",
    "edit profile",
    "abp platform",
    "abp account",
    "practice mode",
    "follow up fee",
    "digital prescription",
    "file formats",
    "completed consultations",
    "new bookings",
    "booking notifications",
    "appointment notifications",
    "notifications for new bookings",
    "monthly payout statement",
    "bank account for payouts",
    "doctor account deactivation",
    "clinic working hours",
    "consultation history",
    "patient appointment records",
}


ABP_SYNONYMS = {
    "earnings": {
        "earning",
        "earnings",
        "income",
        "revenue",
        "payout",
        "payouts",
        "commission",
    },
    "appointments": {
        "appointment",
        "appointments",
        "booking",
        "bookings",
        "schedule",
        "scheduling",
        "slot",
        "slots",
    },
    "consultations": {
        "consultation",
        "consultations",
        "video",
        "meeting",
        "telemedicine",
    },
    "profile": {
        "profile",
        "account",
        "registration",
        "verification",
        "clinic",
        "hospital",
    },
    "payments": {
        "payment",
        "payments",
        "withdrawal",
        "withdrawals",
        "transaction",
        "transactions",
        "fee",
        "fees",
    },
    "notifications": {
        "notification",
        "notifications",
        "booking",
        "bookings",
        "appointment",
        "appointments",
    },
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_abp_related(question: str) -> bool:
    normalized = normalize_text(question)

    if not normalized:
        return False

    # Explicit ABP references are accepted.
    if "abp" in normalized.split():
        return True

    # Check known ABP-specific phrases.
    for phrase in ABP_PHRASES:
        if phrase in normalized:
            return True

    words = set(normalized.split())

    # Check known domain terms.
    if words & ABP_TERMS:
        return True

    # Check combinations of related topic words.
    for topic_words in ABP_SYNONYMS.values():
        if len(words & topic_words) >= 2:
            return True

    return False
