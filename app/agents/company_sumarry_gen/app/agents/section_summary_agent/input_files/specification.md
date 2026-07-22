# Specification File

## System Purpose

Generate tender/proposal document sections using retrieved company context.

---

## Input Parameters

### company_id

Unique company identifier used to retrieve company-specific data.

### section_name

The target section to generate.

Example:

* Company Overview
* Technical Capability
* Infrastructure
* AI Transformation Strategy

### purpose

Explains why the section is being generated.

### retrieved_context

Top relevant chunks retrieved from vector search.

### user_prompt

Additional custom generation instructions.

---

## Generation Requirements

The system must:

1. Analyze retrieved context
2. Understand section purpose
3. Generate relevant proposal content
4. Generate subsection structure
5. Maintain business proposal quality

---

## Retrieval Requirements

The retrieval pipeline must:

* search by company ID
* use semantic similarity
* retrieve top relevant chunks only

---

## Output Schema

Return ONLY valid JSON.

```json
{
  "section_name": "",
  "section_generated_summary": "",
  "subsections": [
    {
      "subsection_name": "",
      "subsection_summary": ""
    }
  ]
}
```

---

## Subsection Rules

Each subsection must:

* support section purpose
* represent meaningful business topics
* use retrieved context
* avoid duplicate concepts

---

## AI Constraints

* No markdown
* No explanations
* No extra text outside JSON
* No hallucinated technical claims
* Keep summaries concise and business-oriented
