# User Prompt – Tender Section Generator Agent

## TASK

Generate a proposal-ready tender section.

You will receive:

* TenderId
* CompanyId
* SectionName
* SectionPurpose
* Retrieved Company Context
* Evidence Summary

Generate:

* GeneratedContent
* CoverageStatus
* EvidenceGap
* MissingEvidenceReasons

## CONTENT REQUIREMENTS

1. Focus on the intent of the SectionName.
2. Address the objectives described in the SectionPurpose.
3. Write complete proposal-ready content suitable for a tender response.
4. Use only supplied evidence and retrieved company context.
5. Use professional and persuasive tender language.
6. Ensure all claims are supported by supplied evidence.
7. Do not repeat information unnecessarily.
8. Maintain a clear and logical narrative structure.

## EVIDENCE RULES

Do not:

* invent evidence
* invent certifications
* invent project experience
* invent case studies
* invent customer references
* invent metrics
* invent performance claims

Use only:

* SectionName
* SectionPurpose
* Retrieved Company Context
* Evidence Summary

## EVIDENCE GAP HANDLING

If evidence is limited:

* Generate the strongest supportable response.
* Use cautious language where necessary.
* Set CoverageStatus to "Partial".
* Set EvidenceGap to true.
* Populate MissingEvidenceReasons only when justified by supplied context.

If evidence is sufficient:

* Set CoverageStatus to "Complete".
* Set EvidenceGap to false.

## OUTPUT REQUIREMENTS

Return only specification-compliant JSON.

Do not return:

* markdown
* explanations
* notes
* reasoning
* commentary

Return only the final JSON object defined in the specification.
