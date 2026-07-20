# Tender Section Writer Specification File

Version: 4.0

## PURPOSE

Define a strict separation between client-visible proposal text and internal evidence/coverage metadata.

## INPUT SCHEMA

```json
{
  "SectionId": "",
  "SectionName": "",
  "Requirements": [
    {
      "RequirementId": "",
      "RequirementText": "",
      "MandatoryFlag": false,
      "RequirementType": "",
      "Priority": ""
    }
  ],
  "EvidenceSummary": [
    {
      "RequirementId": "",
      "EvidenceSummary": "",
      "EvidenceGap": false,
      "EvidenceMatches": [
        {
          "ChunkId": "",
          "SourceDocument": "",
          "SourceTitle": "",
          "Page": null,
          "Score": null,
          "EvidenceText": ""
        }
      ]
    }
  ],
  "ApprovedCommitments": [
    {
      "RequirementId": "",
      "CommitmentText": "",
      "ApprovedBy": "",
      "ApprovalReference": ""
    }
  ],
  "SubSections": [
    {
      "SectionId": "",
      "SectionName": "",
      "Requirements": [],
      "EvidenceSummary": [],
      "ApprovedCommitments": [],
      "SubSections": []
    }
  ],
  "WritingInstruction": {
    "Tone": "professional",
    "TargetAudience": "",
    "MaximumWordCount": null,
    "AllowApprovedCommitments": false,
    "AllowNeutralTenderContext": false
  }
}
```

## INPUT RULES

1. `EvidenceSummary` is the only source of factual company evidence.
2. `ApprovedCommitments` is the only source of future-facing supplier commitments.
3. `EvidenceGap` is internal control data. It must never be translated into client-visible narrative.
4. If `AllowApprovedCommitments` is false, ignore `ApprovedCommitments` for ProposalContent and record the requirement for internal review where necessary.
5. If `AllowNeutralTenderContext` is false, do not create generic explanatory text simply because a SectionName exists.
6. A RequirementId in `EvidenceSummary` or `ApprovedCommitments` must match a RequirementId in the relevant section or subsection.

## OUTPUT SCHEMA

```json
{
  "SectionId": "",
  "SectionName": "",
  "GeneratedContent": "",
  "GeneratedSubSections": [
    {
      "SectionId": "",
      "SectionName": "",
      "GeneratedContent": "",
      "GeneratedSubSections": []
    }
  ],
  "EvaluationCriteria": [
    {
      "CriterionId": "",
      "CriterionName": "",
      "Addressed": true,
      "HowAddressed": ""
    }
  ],
  "InternalReview": {
    "CoverageStatus": "Complete",
    "EvidenceGap": false,
    "PublicationStatus": "Ready",
    "RequirementCoverage": [
      {
        "RequirementId": "",
        "RequirementText": "",
        "Covered": true,
        "CoverageLocation": "Section|SubSection"
      }
    ],
    "MissingEvidence": [
      {
        "RequirementId": "",
        "RequirementText": "",
        "GapType": "NoSupportingEvidence",
        "MissingInformation": [
          ""
        ],
        "RecommendedResolution": ""
      }
    ],
    "UnsupportedClaims": [
      {
        "Claim": "",
        "Reason": ""
      }
    ],
    "Traceability": [
      {
        "RequirementId": "",
        "ContentLocation": "Section|SubSection",
        "EvidenceChunkIds": [],
        "ApprovedCommitmentReferences": []
      }
    ],
    "QualityChecks": {
      "RequirementsCovered": true,
      "EvaluationCriteriaCovered": true,
      "EvidenceGrounded": true,
      "NoHallucinations": true,
      "CaseStudyIncluded": true,
      "WinThemesIncluded": true
    }
  }
}

```

## ENUMERATIONS

### CoverageStatus

- `Complete` — every relevant requirement has sufficient approved support.
- `Partial` — one or more requirements have some support but one or more material elements remain unsupported.
- `InsufficientEvidence` — no usable approved support exists for one or more required content elements.
- `NotApplicable` — all relevant requirements have been explicitly marked not applicable.

### PublicationStatus

- `Ready` — proposal content contains supported statements and no mandatory requirement is unresolved.
- `ReviewRequired` — content may be reviewed, but one or more non-mandatory requirements are incomplete or need evidence confirmation.
- `Blocked` — one or more mandatory requirements lack sufficient approved evidence or an approved commitment.

### GapType

- `NoSupportingEvidence`
- `PartialSupportingEvidence`
- `EvidenceConflict`
- `ApprovedCommitmentRequired`
- `NotApplicable`

## OUTPUT RULES

1. `GeneratedContent` and `GeneratedSubSections[].GeneratedContent` are proposal-visible fields.
2. `InternalReview` is not proposal-visible and must not be rendered in the section-detail page, preview or exported proposal.
3. Preserve SectionId, SectionName and SubSection hierarchy.
4. When SubSections exist:
   - parent `GeneratedContent` must be a short introduction only;
   - detailed content belongs in the relevant GeneratedSubSections.
5. When no SubSections exist:
   - generate content in the parent `GeneratedContent`;
   - return `GeneratedSubSections` as `[]`.
6. When a subsection has no usable evidence or permitted approved commitment:
   - return `GeneratedContent` as `""`;
   - add the precise issue in `InternalReview.MissingEvidence`;
   - set PublicationStatus according to whether the requirement is mandatory.
7. Do not add a `CoverageStatus` or `EvidenceGap` field inside `GeneratedContent` or any generated subsection.
8. Do not write evidence availability, evidence gaps, source names, internal verification status or unsupported-claim caveats in proposal-visible fields.
9. `Traceability` is internal-only. It supports audit, review and grounding validation.
10. Return strict JSON only. Do not return markdown, prose or explanatory text outside the JSON object.

## UI / ASSEMBLY REQUIREMENT

The Proposal Editor must bind only these fields into the client-facing section view:

- `SectionId`
- `SectionName`
- `GeneratedContent`
- `GeneratedSubSections[].SectionId`
- `GeneratedSubSections[].SectionName`
- `GeneratedSubSections[].GeneratedContent`

The following must be stored and shown only in the internal review/evidence workspace:

- `InternalReview`
- Evidence chunk identifiers and source references
- CoverageStatus
- EvidenceGap
- MissingEvidence
- PublicationStatus
- Traceability

A proposal cannot be exported when any required section has `PublicationStatus = "Blocked"`.
