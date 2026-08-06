# Task

You will receive multiple tender document chunks.

Analyze every chunk independently.

A supplier requirement is any statement requiring the supplier, bidder, contractor, consultant, or service provider to provide, perform, submit, maintain, comply with, demonstrate, or deliver something.

For every detected requirement return:

- RequirementText
- RequirementType
- RequirementStrength
- MandatoryFlag
- Priority
- Confidence
- CapabilityIntent
- EvidenceSections
- SemanticAnchors
- IntentConfidence

Rules

- Do not merge independent requirements.
- Preserve the original meaning.
- MandatoryFlag must be true when RequirementStrength is Mandatory.
- Confidence values must be between 0.00 and 1.00.
- Semantic Anchors should contain only explicit or clearly implied business concepts.
- Use only predefined taxonomy values.

Output format

{
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "detection_result": true,
      "requirements": [
        {
          "RequirementText": "",
          "RequirementType": "",
          "RequirementStrength": "",
          "MandatoryFlag": true,
          "Priority": "",
          "Confidence": 0.98,
          "CapabilityIntent": [],
          "EvidenceSections": [],
          "SemanticAnchors": [],
          "IntentConfidence": 0.95
        }
      ]
    },
    {
      "chunk_id": "chunk_002",
      "detection_result": false,
      "requirements": []
    }
  ]
}