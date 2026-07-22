# Tender Section Generator Specification

Version: 1.0

## INPUT SCHEMA

```json
{
  "TenderId": "",
  "CompanyId": "",
  "SectionName": "",
  "SectionPurpose": ""
}
```
## OUTPUT SCHEMA

```json
{
  "SectionId": "",
  "SectionName": "",
  "GeneratedContent": "",
  "CoverageStatus": "",
  "EvidenceGap": false,
  "MissingEvidenceReasons": [
    {
      "RequirementId": "",
      "RequirementText": "",
      "EvidenceRetrievalStatus": "",
      "EvidenceConfidence": 0.0,
      "MissingEvidenceReason": ""
    }
  ],
  "GeneratedSubSections": [
    {
      "SectionId": "",
      "SectionName": "",
      "GeneratedContent": "",
      "CoverageStatus": "",
      "EvidenceGap": false,
      "MissingEvidenceReasons": [
        {
          "RequirementId": "",
          "RequirementText": "",
          "EvidenceRetrievalStatus": "",
          "EvidenceConfidence": 0.0,
          "MissingEvidenceReason": ""
        }
      ]
    }
  ]
}
```

### Output Rules

1. Return only the OUTPUT SCHEMA.
2. Preserve SectionId exactly as supplied.
3. Preserve SectionName exactly as supplied.
4. GeneratedContent must contain the complete proposal-ready section.
5. Generate subsection entries when logical subsection content exists.
6. CoverageStatus values:

   * Complete
   * Partial
7. EvidenceGap:

   * false when evidence sufficiently supports generated content.
   * true when evidence is incomplete or insufficient.
8. MissingEvidenceReasons must contain only genuine evidence gaps.
9. If no evidence gaps exist, return an empty array.
10. GeneratedSubSections must always be present.
11. If no subsections are generated, return an empty array.
12. Use only retrieved evidence and supplied context.
13. Do not invent evidence.
14. Do not invent certifications.
15. Do not invent project experience.
16. Do not invent metrics or performance claims.
17. Do not return markdown.
18. Do not return explanations.
19. Do not return reasoning.
20. Return valid JSON only.
