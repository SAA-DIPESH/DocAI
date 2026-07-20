# Specification — CPV Query Variant & Anchor Tag Generation Agent

## 1. Purpose

Transform a CPV code and industry into a retrieval plan for finding company-profile chunks relevant to an evidence-backed Win Theme analysis.

This agent only designs the retrieval plan. It does **not** call Qdrant, generate embeddings, retrieve documents, fuse results, or produce the final Win Theme.

The orchestration layer is responsible for:

- Embedding the generated queries.
- Executing semantic searches against Qdrant.
- Applying mandatory company filters.
- Fusing and deduplicating results.
- Passing retrieved evidence to the Win Theme Agent.

---

## 2. Required Input

```json
{
  "request_id": "{{request_id}}",
  "company_id": "{{company_id}}",
  "industry": "{{industry}}",
  "cpv_code": "{{cpv_code}}"
}
```

---

## 3. Processing Flow

1. Validate that all required inputs are present.
2. Analyse the CPV code together with the industry.
3. Classify the procurement context:
   - Procurement type
   - Procurement domain
   - Buyer sector context
4. Select the relevant retrieval dimensions.
5. Generate retrieval anchor groups.
6. Generate:
   - Anchor tags
   - Anchor query
   - Query variants
7. Validate the generated retrieval plan before returning it.

---

## 4. Standard Retrieval Dimensions

Use all relevant dimensions. Omit only those that are genuinely irrelevant.

| Anchor ID | Retrieval Objective |
|-----------|---------------------|
| `DOMAIN_OFFERING_FIT` | Evidence that the organisation delivers the required goods, works or services. |
| `RELEVANT_TRACK_RECORD` | Comparable contracts, projects, assignments, outcomes and client references. |
| `DELIVERY_METHOD_ASSURANCE` | Mobilisation, planning, governance, quality, risk, performance and continuity. |
| `PEOPLE_CAPACITY_RESOURCES` | Relevant people, qualifications, workforce capacity, facilities, equipment or supply chain. |
| `COMPLIANCE_SAFETY_STANDARDS` | Applicable regulations, certifications, safety, quality, environmental or safeguarding evidence. |
| `OUTCOMES_VALUE_IMPROVEMENT` | Measurable service, cost, time, quality, social, environmental or operational outcomes. |
| `DIFFERENTIATORS_REUSABLE_ADVANTAGES` | Practical assets, methods, partnerships, processes or innovations supported by evidence. |

---

## 5. Generated JSON Contract

```json
{
  "schema_version": "1.0",
  "request_id": "{{request_id}}",
  "status": "ready | invalid_input",
  "input": {
    "company_id": "{{company_id}}",
    "industry": "{{industry}}",
    "cpv_code": "{{cpv_code}}"
  },
  "procurement_context": {
    "procurement_type": "works | supplies | services | mixed | unresolved",
    "procurement_domain": "{{domain_name}}",
    "domain_confidence": "high | medium | low",
    "domain_rationale": "{{short_reason}}",
    "buyer_sector_context": {
      "mode": "industry_explicit | cpv_inferred | cross_sector | unresolved",
      "primary_context": "{{sector_or_cross_sector_label}}",
      "candidate_contexts": [
        "{{candidate_1}}"
      ],
      "rationale": "{{short_reason}}"
    }
  },
  "anchor_groups": [
    {
      "anchor_id": "DOMAIN_OFFERING_FIT",
      "objective": "{{evidence objective}}",
      "anchor_tags": [
        "{{tag_1}}",
        "{{tag_2}}",
        "{{tag_3}}",
        "{{tag_4}}",
        "{{tag_5}}"
      ],
      "anchor_query": "{{compact domain-aware semantic query}}",
      "query_variants": [
        "{{natural-language evidence query 1}}",
        "{{natural-language evidence query 2}}"
      ],
      "preferred_document_types": [
        "CaseStudy",
        "CapabilityStatement"
      ],
      "metadata_should_match": {
        "sector": [
          "{{sector_or_domain_tag}}"
        ],
        "offering_category": [
          "{{offering_tag}}"
        ],
        "evidence_type": [
          "CaseStudy",
          "ContractReference"
        ]
      },
      "extract_for_win_theme": [
        "{{field_1}}",
        "{{field_2}}"
      ],
      "search_priority": 1
    }
  ],
  "execution_limits": {
    "max_anchor_groups": 7,
    "max_query_variants_per_group": 3,
    "max_total_semantic_queries": 28
  },
  "validation": {
    "warnings": [],
    "assumptions": []
  }
}
```

---

## 6. Output Validation

A `ready` output must satisfy all of the following:

- Required input fields are present.
- Procurement domain is distinct from buyer sector context.
- 4–7 anchor groups are generated.
- Every anchor group contains:
  - 5–12 anchor tags
  - One anchor query
  - 2–3 query variants
- Query variants are tailored to the procurement domain.
- Queries request verifiable company evidence.
- No output claims that the company possesses any capability, experience, certification or outcome.

---

## 7. Invalid Input Response

If required input is missing, return only:

```json
{
  "schema_version": "1.0",
  "request_id": "{{request_id}}",
  "status": "invalid_input",
  "input": {
    "company_id": "{{company_id}}",
    "industry": "{{industry}}",
    "cpv_code": "{{cpv_code}}"
  },
  "validation": {
    "warnings": [
      "Missing required input."
    ],
    "assumptions": []
  }
}
```

---

## 8. Orchestration Responsibilities

The orchestration layer must:

1. Generate embeddings for every `anchor_query` and `query_variant`.
2. Execute semantic searches against Qdrant.
3. Apply the mandatory `company_id` filter.
4. Optionally apply metadata filters when available.
5. Fuse search results.
6. Remove duplicate chunks.
7. Preserve source metadata and retrieval scores.
8. Pass retrieved chunks to the Win Theme Agent.

---

## 9. Guardrails

- This agent must **not** retrieve documents.
- This agent must **not** generate Win Themes.
- This agent must **not** summarize company information.
- This agent must **not** assume company capabilities.
- All generated queries must remain evidence-focused.
- Do not use generic marketing language.
- Do not introduce unsupported sector assumptions.
- Keep retrieval queries concise, specific and domain-aware.