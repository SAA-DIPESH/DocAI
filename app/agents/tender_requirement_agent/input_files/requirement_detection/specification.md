# Requirement Detection & Extraction Specification

## Objective

Analyze a tender document chunk and identify every explicit supplier requirement.

If no supplier requirement exists, return an empty list.

Each extracted requirement must be represented as a structured object with classification metadata.

---

## What is a Requirement?

A requirement is any statement that specifies something the supplier, bidder, contractor, vendor, or service provider is expected, required, requested, or instructed to provide, perform, demonstrate, submit, comply with, maintain, or deliver.

Requirements may be:

- Mandatory
- Optional
- Conditional
- Informational

---

## Extract Requirements

Extract each requirement as an independent requirement.

Do NOT merge multiple requirements into one.

For example:

Supplier shall:

- maintain ISO27001 certification
- provide 24x7 support
- appoint a dedicated project manager

must produce three separate requirements.

---

## Requirement Fields

For every requirement return:

### RequirementText

The exact supplier requirement.

Do not rewrite unless required to remove unnecessary surrounding context.

---

### RequirementType

Choose the most appropriate category.

Allowed values include:

- Certification
- Compliance
- Security
- Technical Capability
- Functional Requirement
- Non-Functional Requirement
- Staffing
- Experience
- Financial
- Commercial
- Pricing
- Insurance
- Legal
- Governance
- Reporting
- Documentation
- Deliverable
- Timeline
- Support
- Training
- Service Level
- Submission
- Selection Criteria
- Evaluation Criteria
- Contract
- Environmental
- Sustainability
- Health & Safety
- Data Protection
- Other

---

### RequirementStrength

Choose exactly one:

- Mandatory
- Conditional
- Optional
- Informational

Examples

Mandatory

- shall
- must
- required
- mandatory
- will be rejected

Conditional

- if applicable
- where required
- if selected

Optional

- may
- can
- optional
- preferred

Informational

Statements that provide context but do not require supplier action.

---

### MandatoryFlag

Return:

true

or

false

MandatoryFlag should be true whenever RequirementStrength is Mandatory.

---

### Priority

Choose:

- High
- Medium
- Low

Examples

High

- legal
- compliance
- security
- mandatory submission
- eligibility
- contract award
- pass/fail

Medium

- technical capability
- staffing
- delivery
- methodology

Low

- recommendations
- best practice
- optional information

---

### Confidence

Return a decimal number between

0.00

and

1.00

representing confidence in the extraction.

---

## Output Rules

Return ONLY valid JSON.

Never return markdown.

Never explain your reasoning.

---

## Output Schema

```json
{
  "detection_result": true,
  "requirements": [
    {
      "RequirementText": "",
      "RequirementType": "",
      "RequirementStrength": "",
      "MandatoryFlag": true,
      "Priority": "",
      "Confidence": 0.98
    }
  ]
}
```

If no requirements are detected

```json
{
  "detection_result": false,
  "requirements": []
}
```