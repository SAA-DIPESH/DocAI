from __future__ import annotations

from typing import Any


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        values = [values]

    return {
        str(value).strip().casefold()
        for value in values
        if value is not None and str(value).strip()
    }


def _intent_values(
    requirement: dict[str, Any],
    intent_key: str,
    aggregate_key: str,
) -> set[str]:
    values: list[Any] = []

    intent_result = requirement.get("IntentResult")
    if isinstance(intent_result, dict):
        raw_value = intent_result.get(intent_key)

        if isinstance(raw_value, list):
            values.extend(raw_value)
        elif raw_value is not None:
            values.append(raw_value)

    aggregate_value = requirement.get(aggregate_key)
    if isinstance(aggregate_value, list):
        values.extend(aggregate_value)
    elif aggregate_value is not None:
        values.append(aggregate_value)

    return _string_set(values)


def _contains_any(
    text: str,
    phrases: tuple[str, ...],
) -> bool:
    return any(phrase in text for phrase in phrases)


def classify_requirement(
    requirement: dict[str, Any],
) -> dict[str, Any]:
    source_requirements = [
        item
        for item in _list(requirement.get("SourceRequirements"))
        if isinstance(item, dict)
    ]

    source_texts = [
        str(item.get("RequirementText") or "") for item in source_requirements
    ]

    source_types = [
        item.get("RequirementType")
        for item in source_requirements
        if item.get("RequirementType")
    ]

    semantic_anchors = _intent_values(
        requirement,
        "SemanticAnchors",
        "SemanticAnchors",
    )

    text = " ".join(
        [
            str(requirement.get("CanonicalRequirement") or ""),
            *[str(value) for value in _list(requirement.get("Headings"))],
            *source_texts,
            *semantic_anchors,
        ]
    ).casefold()

    types = _string_set(
        [
            requirement.get("RequirementType"),
            *_list(requirement.get("RequirementTypes")),
            *source_types,
        ]
    )

    capability_intents = _intent_values(
        requirement,
        "CapabilityIntent",
        "CapabilityIntents",
    )

    evidence_sections = _intent_values(
        requirement,
        "EvidenceSections",
        "EvidenceSections",
    )

    submission_phrases = (
        "closing date",
        "submission deadline",
        "deadline for",
        "deadline to",
        "submit through",
        "submit via",
        "upload via",
        "upload to",
        "e-tendering portal",
        "procurement portal",
        "procurement documentation via",
        "documents are accessible",
        "documents and opportunity notice",
        "contract finder url",
        "answers for the technical question need to be within a pdf",
        "within a pdf",
        "cells in this colour",
        "automatic formulas",
        "supplier registration process",
        "supplier qualification process",
        "bank details questionnaire",
        "tick that you have read",
        "terms of use",
        "privacy policy statement",
        "complete the relevant sheets",
        "must apply",
        "how to apply",
    )

    metadata_phrases = (
        "contract start date",
        "contract starts on",
        "contract starts from",
        "contract commences on",
        "contract commencement date",
        "contract end date",
        "contract ends on",
        "contract location",
        "contract value",
        "estimated contract value",
        "contract type",
        "procedure type",
        "procurement procedure",
        "is suitable for",
        "are to be appointed",
        "is designed to meet",
        "requirement is split",
        "opportunity is split",
        "dynamic purchasing system",
    )

    declaration_phrases = (
        "must declare",
        "shall declare",
        "must confirm",
        "shall confirm",
        "must certify",
        "shall certify",
        "supplier warrants",
        "supplier certifies",
        "supplier confirms",
        "supplier accepts",
        "supplier agrees",
        "supplier declares",
        "supplier acknowledges",
        "must acknowledge",
        "shall acknowledge",
        "must agree",
        "shall agree",
        "must accept",
        "shall accept",
        "demonstrate compliance",
        "mandatory declaration",
        "must hold",
        "minimum qualification",
        "enter into a confidentiality agreement",
        "must enter into a direct confidentiality agreement",
    )

    contractual_context_phrases = (
        "will indemnify",
        "shall indemnify",
        "will be liable",
        "shall be liable",
        "during its lifetime",
        "during its life",
        "terminated early",
        "in accordance with its terms",
        "contractual terms",
        "contract duration",
        "won't be excused from any obligation",
        "won’t be excused from any obligation",
        "will not be excused from any obligation",
        "may disclose confidential information",
    )

    response_types = {
        "technical",
        "technical capability",
        "commercial",
        "pricing",
        "staffing",
        "quality",
        "deliverable",
        "governance",
        "reporting",
        "security",
        "data protection",
        "implementation",
        "service delivery",
        "resource management",
        "non-functional requirement",
        "functional requirement",
        "health & safety",
        "health and safety",
    }

    response_intents = {
        "technical capability",
        "service delivery",
        "quality assurance",
        "staffing",
        "resource management",
        "commercial",
        "governance",
        "reporting",
        "security",
        "project management",
        "functional capability",
        "logistics",
        "health & safety",
        "health and safety",
    }

    response_evidence_sections = {
        "technical solution",
        "methodology",
        "implementation plan",
        "project plan",
        "delivery approach",
        "pricing",
        "commercial response",
        "resource plan",
        "team",
        "key personnel",
        "quality management",
        "governance",
        "security",
        "reporting",
        "services",
        "training",
        "health & safety",
        "health and safety",
    }

    response_phrases = (
        "describe ",
        "explain ",
        "demonstrate ",
        "provide details",
        "provide evidence",
        "provide a completed",
        "please describe",
        "please explain",
        "please demonstrate",
        "please provide",
        "please complete the rate card",
        "please complete solution delivery costs",
        "please complete assumptions",
        "tenderer shall provide",
        "tenderer must provide",
        "supplier shall provide",
        "supplier must provide",
        "supplier must ensure",
        "supplier will ensure",
        "supplier shall ensure",
        "supplier must maintain",
        "supplier will maintain",
        "supplier must allocate",
        "supplier shall manage",
        "supplier must manage",
        "supplier shall deliver",
        "supplier must deliver",
        "supplier shall implement",
        "supplier must implement",
        "supplier shall assure",
        "supplier must assure",
        "supplier shall price",
        "supplier must price",
        "supplier shall resource",
        "supplier must resource",
        "supplier shall staff",
        "supplier must staff",
        "supplier shall report",
        "supplier must report",
        "supplier shall operate",
        "supplier must operate",
        "supplier must replace",
        "supplier will replace",
        "supplier will immediately remove",
        "response must include",
        "resources you will provide",
        "roles, skills and experience",
        "total cost of delivery",
        "solution delivery costs",
        "rate card",
        "perform their assignment with all due skill",
    )

    disposition: str
    applicable: bool
    reason: str
    confidence: float

    # Submission mechanics must remain narrowly classified.
    if _contains_any(text, submission_phrases):
        disposition = "SUBMISSION_INSTRUCTION"
        applicable = False
        reason = (
            "Source contains submission mechanics, portal instructions, "
            "file-format rules, or registration steps."
        )
        confidence = 0.97

    elif _contains_any(text, metadata_phrases):
        disposition = "TENDER_METADATA"
        applicable = False
        reason = (
            "Source describes tender metadata, procurement structure, "
            "location, dates, or market context."
        )
        confidence = 0.97

    elif _contains_any(text, declaration_phrases):
        disposition = "ELIGIBILITY_OR_DECLARATION"
        applicable = True
        reason = (
            "Source requires a supplier declaration, confirmation, "
            "acknowledgement, certification, or agreement."
        )
        confidence = 0.94

    elif _contains_any(text, contractual_context_phrases) and not _contains_any(
        text, response_phrases
    ):
        disposition = "CONTRACTUAL_CONTEXT"
        applicable = False
        reason = (
            "Source describes contractual liability, indemnity, lifecycle, "
            "or legal allocation without requesting proposal content."
        )
        confidence = 0.93

    elif (
        bool(types.intersection(response_types))
        or bool(capability_intents.intersection(response_intents))
        or bool(evidence_sections.intersection(response_evidence_sections))
        or _contains_any(text, response_phrases)
    ):
        disposition = "RESPONSE_CONTENT"
        applicable = True
        reason = (
            "Requirement type, capability intent, evidence section, or "
            "source wording requires supplier response content."
        )
        confidence = 0.94

    elif "submission" in types or capability_intents == {"submission"}:
        disposition = "SUBMISSION_INSTRUCTION"
        applicable = False
        reason = (
            "Source is classified as a submission-only instruction and "
            "contains no separate proposal response requirement."
        )
        confidence = 0.9

    else:
        disposition = "REVIEW_REQUIRED"
        applicable = False
        reason = (
            "Available requirement text and metadata do not support a "
            "reliable automatic classification."
        )
        confidence = 0.6

    source_confidences = [
        float(item["Confidence"])
        for item in source_requirements
        if isinstance(
            item.get("Confidence"),
            (int, float),
        )
    ]

    if source_confidences:
        average_source_confidence = sum(source_confidences) / len(source_confidences)

        confidence = round(
            min(
                confidence,
                average_source_confidence,
            ),
            4,
        )

    return {
        "Disposition": disposition,
        "ResponseApplicability": applicable,
        "DispositionReason": reason,
        "DispositionConfidence": confidence,
    }
