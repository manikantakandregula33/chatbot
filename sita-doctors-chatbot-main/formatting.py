import re


_ACTION = (
    r"(?:go to|navigate to|open|click|check|ensure|confirm|enter|use|select|choose|"
    r"update|contact|verify|look for|review|wait|save|reconnect|search|locate|"
    r"allow|try|make sure|provide|set|upload|download|remove|add|visit|scroll)"
)
_ACTION_START = re.compile(rf"^(?:please\s+)?{_ACTION}\b", re.IGNORECASE)
_ACTION_ANYWHERE = re.compile(rf"\b{_ACTION}\b", re.IGNORECASE)
_ACTION_SEPARATOR = re.compile(
    rf"(?:,\s*|\s+and\s+|\s+then\s+)(?=(?:please\s+)?{_ACTION}\b)",
    re.IGNORECASE,
)
_SENTENCE_SEPARATOR = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_UPDATE_DETAILS = re.compile(
    r"^(You can update your )(.+?)(\.\s*Verified medical credentials .+)$",
    re.IGNORECASE,
)


def _format_update_details(answer: str) -> str | None:
    match = _UPDATE_DETAILS.match(answer.strip())
    if not match:
        return None

    fields = [field.strip() for field in match.group(2).split(",")]
    if fields:
        fields[-1] = re.sub(r"^and\s+", "", fields[-1], flags=re.IGNORECASE)
    if len(fields) < 2 or any(not field for field in fields):
        return None

    heading = match.group(1).strip().removesuffix(" your").capitalize()
    bullets = "\n".join(f"- {field}" for field in fields)
    return f"**{heading}**\n\n{bullets}\n\n{match.group(3).strip().lstrip('. ')}"


def format_answer_for_display(answer: str) -> str:
    """Add markdown list structure only when the approved wording has clear actions."""
    details_list = _format_update_details(answer)
    if details_list is not None:
        return details_list

    sentences = _SENTENCE_SEPARATOR.split(answer.strip())
    parts: list[tuple[str, bool]] = []

    for sentence in sentences:
        sentence = sentence.strip()
        if re.match(r"^(?:if|when|once|after|before)\b", sentence, re.IGNORECASE):
            parts.append((sentence, bool(_ACTION_ANYWHERE.search(sentence))))
            continue
        clauses = _ACTION_SEPARATOR.split(sentence)
        for clause in clauses:
            part = clause.strip()
            if not part:
                continue
            parts.append((part, bool(_ACTION_START.match(part))))

    action_count = sum(is_action for _, is_action in parts)
    if action_count < 2:
        return answer

    blocks: list[str] = []
    pending_steps: list[str] = []
    heading_added = False

    def flush_steps() -> None:
        nonlocal heading_added
        if not pending_steps:
            return
        if not heading_added:
            blocks.append("**Steps to follow**")
            heading_added = True
        blocks.append("\n".join(f"- {step}" for step in pending_steps))
        pending_steps.clear()

    for part, is_action in parts:
        if is_action:
            step = part.rstrip(" ,;")
            if step and step[-1] not in ".!?":
                step += "."
            if step:
                pending_steps.append(step[0].upper() + step[1:])
        else:
            flush_steps()
            blocks.append(part)
    flush_steps()
    return "\n\n".join(blocks)
