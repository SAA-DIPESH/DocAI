# Improvement Specification

## Inputs

The system will receive:

* company_id
* section_name
* section_summary
* subsection summaries
* purpose
* instruction
* retrieved context

---

## Objective

Improve the existing tender/proposal section according to user instructions.

---

## Improvement Rules

The AI must:

* enhance business quality
* improve clarity
* improve enterprise positioning
* improve proposal impact
* preserve technical accuracy

---

## Subsection Rules

Subsections must:

* remain relevant to section purpose
* align with user instructions
* maintain proposal consistency

---

## Output Schema

Return ONLY valid JSON.

```json
{
  "section_name": "",
  "improved_section_summary": "",
  "subsections": [
    {
      "subsection_name": "",
      "improved_subsection_summary": ""
    }
  ]
}
```
