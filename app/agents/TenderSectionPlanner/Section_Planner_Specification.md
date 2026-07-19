# Section Planner Specification

Return strict JSON matching exactly:

```json
{"ProposalGroups":[{"GroupName":"Technical Response","Sections":[{"SectionName":"Solution Approach","SectionDescription":"Concise source-grounded response scope.","SubSections":[{"SubSectionName":"Architecture","SubSectionDescription":"Concise source-grounded subsection scope.","CanonicalRequirementIds":["<exact source ID>"],"EvaluationCriterionIds":[]}]}]}],"UnmappedCanonicalRequirementIds":[],"UnmappedEvaluationCriterionIds":[]}
```

No markdown, explanations, extra fields, final structural IDs, weights,
evidence, lineage, statuses, validation, traceability, or persistence metadata.
Names must be concise and unique within their parent. Descriptions must be
source-grounded and concise. Copy source IDs exactly.
