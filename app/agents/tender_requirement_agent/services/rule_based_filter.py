import re
from typing import Tuple

# Words commonly found in tender requirements
REQUIREMENT_KEYWORDS = {
    # Obligation
    "shall",
    "must",
    "should",
    "required",
    "mandatory",
    "require",
    "requires",
    "need",
    "needs",

    # Parties
    "bidder",
    "contractor",
    "vendor",
    "supplier",
    "consultant",
    "service provider",

    # Actions
    "submit",
    "provide",
    "maintain",
    "install",
    "deliver",
    "ensure",
    "perform",
    "execute",
    "comply",
    "compliance",

    # Eligibility
    "eligible",
    "eligibility",
    "qualification",
    "experience",
    "certificate",
    "certification",
    "license",
    "registration",

    # Technical
    "technical",
    "specification",
    "criteria",
    "standard",

    # Financial
    "emd",
    "security deposit",
    "performance bank guarantee",
    "turnover",
}

# Common requirement sentence patterns
REQUIREMENT_PATTERNS = [
    r"\bshall\b",
    r"\bmust\b",
    r"\bis required to\b",
    r"\bmandatory\b",
    r"\bthe bidder shall\b",
    r"\bthe contractor shall\b",
    r"\bthe vendor shall\b",
    r"\bthe supplier shall\b",
    r"\bminimum\b",
    r"\bat least\b",
]


def rule_based_filter(chunk_text: str) -> Tuple[bool, str]:
    """
    Returns:
        (should_process, reason)
    """

    if not chunk_text or not chunk_text.strip():
        return False, "Empty chunk"

    text = chunk_text.lower()

    matched_keywords = [
        kw for kw in REQUIREMENT_KEYWORDS
        if kw in text
    ]

    matched_patterns = [
        pattern for pattern in REQUIREMENT_PATTERNS
        if re.search(pattern, text)
    ]

    score = 0
    score += len(matched_keywords)
    score += len(matched_patterns) * 2

    if score >= 2:
        return (
            True,
            f"Matched keywords={matched_keywords}, patterns={matched_patterns}",
        )

    return (
        False,
        "No requirement indicators found",
    )