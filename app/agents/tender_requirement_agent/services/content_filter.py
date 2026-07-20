import re
from typing import Tuple

# =====================================================
# Keyword Weights
# =====================================================

HIGH_WEIGHT_KEYWORDS = {
    "shall": 5,
    "must": 5,
    "mandatory": 5,
    "required": 5,
    "require": 5,
    "requires": 5,
}

MEDIUM_WEIGHT_KEYWORDS = {
    "bidder": 3,
    "contractor": 3,
    "vendor": 3,
    "supplier": 3,
    "consultant": 3,
    "service provider": 3,

    "submit": 3,
    "provide": 3,
    "maintain": 3,
    "install": 3,
    "deliver": 3,
    "ensure": 3,
    "perform": 3,
    "execute": 3,
    "comply": 3,
    "compliance": 3,

    "eligible": 3,
    "eligibility": 3,
    "qualification": 3,
    "experience": 3,
    "certificate": 3,
    "certification": 3,
    "license": 3,
    "registration": 3,
}

LOW_WEIGHT_KEYWORDS = {
    "technical": 1,
    "specification": 1,
    "criteria": 1,
    "standard": 1,
    "turnover": 1,
    "emd": 1,
    "security deposit": 1,
    "performance bank guarantee": 1,
}

# =====================================================
# Regex Patterns
# =====================================================

PATTERN_WEIGHTS = {
    r"\bshall\b": 5,
    r"\bmust\b": 5,
    r"\bis required to\b": 6,
    r"\bmandatory\b": 5,
    r"\bthe bidder shall\b": 7,
    r"\bthe contractor shall\b": 7,
    r"\bthe vendor shall\b": 7,
    r"\bthe supplier shall\b": 7,
    r"\bminimum\b": 4,
    r"\bat least\b": 4,
}


def contains_keyword(text: str, keyword: str) -> bool:
    """
    Matches whole words for single-word keywords and
    substring matching for multi-word phrases.
    """

    if " " in keyword:
        return keyword in text

    pattern = rf"\b{re.escape(keyword)}\b"
    return re.search(pattern, text) is not None


# =====================================================
# Content Filter
# =====================================================

def content_filter(chunk_text: str) -> Tuple[int, str]:
    """
    Calculates a requirement likelihood score from chunk text.

    Returns:
        score
        reason
    """

    if not chunk_text or not chunk_text.strip():
        return 0, "Empty chunk"

    text = chunk_text.lower()

    score = 0
    reasons = []

    # =====================================================
    # High Weight Keywords
    # =====================================================

    matched = []

    for keyword, weight in HIGH_WEIGHT_KEYWORDS.items():

        if contains_keyword(text, keyword):
            score += weight
            matched.append(keyword)

    if matched:
        reasons.append(f"High={matched}")

    # =====================================================
    # Medium Weight Keywords
    # =====================================================

    matched = []

    for keyword, weight in MEDIUM_WEIGHT_KEYWORDS.items():

        if contains_keyword(text, keyword):
            score += weight
            matched.append(keyword)

    if matched:
        reasons.append(f"Medium={matched}")

    # =====================================================
    # Low Weight Keywords
    # =====================================================

    matched = []

    for keyword, weight in LOW_WEIGHT_KEYWORDS.items():

        if contains_keyword(text, keyword):
            score += weight
            matched.append(keyword)

    if matched:
        reasons.append(f"Low={matched}")

    # =====================================================
    # Regex Patterns
    # =====================================================

    matched_patterns = []

    for pattern, weight in PATTERN_WEIGHTS.items():

        if re.search(pattern, text):
            score += weight
            matched_patterns.append(pattern)

    if matched_patterns:
        reasons.append(f"Patterns={matched_patterns}")

    # =====================================================
    # Final
    # =====================================================

    if not reasons:
        reasons.append("No content indicators")

    return score, " | ".join(reasons)