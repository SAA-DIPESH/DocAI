# Specification — Company Capability Win Theme Generation Agent

## Purpose

Convert one company evidence set into one reusable, evidence-backed company capability win theme.

The generated theme should describe a meaningful organisational capability that can later be adapted to specific procurement opportunities.

---

## Input

Use the supplied request contract.

### Context
- request_id
- company_id

### Anchor Group
- anchor_group.anchor_id
- objective
- anchor_query
- query_variants

### Retrieved Evidence
A collection of company-document excerpts with:
- evidence_id
- document_id
- excerpt
- retrieval metadata

---

## Processing

1. Validate all required inputs.
2. Validate evidence thresholds.
3. Identify explicit company capabilities supported by the supplied evidence.
4. Remove duplicate or overlapping capabilities.
5. Select the strongest evidence-backed capability that best satisfies the anchor objective.
6. Derive a concise customer benefit directly supported by the capability.
7. Generate one reusable capability win theme.
8. Preserve evidence traceability through supporting evidence IDs.
9. Record any evidence limitations.

---

## Output Contract

```json
{
  "company_id": "{{company_id}}",
  "anchor_id": "{{anchor_id}}",
  "status": "candidate | insufficient_evidence",
  "win_theme": {
    "theme_name": "{{3-8 word title}}",
    "theme_statement": "{{One evidence-backed sentence describing the company capability and customer benefit}}",
    "customer_value": "{{Practical value delivered by the capability}}",
    "theme_type": "company_capability",
    "supporting_evidence_ids": [
      "EV-001",
      "EV-002"
    ],
    "proof_points": [
      "{{Explicit evidence}}"
    ],
    "confidence": "high | medium | low",
    "evidence_gaps": []
  },
  "validation": {
    "warnings": [],
    "unsupported_claims_removed": []
  }
}
```

---

## Confidence Rules

### High
- Capability consistently supported by multiple evidence items across multiple documents.

### Medium
- Capability supported by sufficient evidence with limited corroboration.

### Low
- Capability meets the minimum evidence threshold but has limited supporting evidence.

---

## Failure Contract

When evidence thresholds are not met:

- Return `status: "insufficient_evidence"`.
- Set `win_theme` to `null`.
- Describe only the evidence gap inside `validation.warnings`.

Do not generate speculative content.

---

## Constraints

- `theme_name`: 3–8 words.
- `theme_statement`: maximum 45 words.
- `customer_value`: maximum 25 words.
- `proof_points`: maximum 3.
- Every statement must be directly supported by the supplied evidence.
- Do not generate procurement-specific, buyer-specific or tender-specific claims.
- Do not include citations, markdown, links or explanatory text outside the JSON object.