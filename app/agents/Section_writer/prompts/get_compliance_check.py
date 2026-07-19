from langchain_core.prompts import ChatPromptTemplate

COMPLIANCE_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert Proposal Compliance Reviewer..."),  # Standard practice is to put the system instructions here directly, or pass a system variable if defined elsewhere
    (
        "human",
        """
Generated Proposal:
{generated_content}

Section Context:
{section_context}

Your responsibility is to review a generated proposal section.
You MUST NOT rewrite the proposal.
Your job is ONLY to verify whether the generated proposal complies with the provided context.

You are given:
1. Generated Proposal Section
2. Section Metadata
3. Evidence Summary
4. Evaluation Criteria
5. Win Themes

Evaluate the proposal using the following checklist:

1. Requirement Coverage
- Does the proposal address every requirement?
- Are any requirements missing?

2. Evidence Grounding
- Are all factual statements supported by the evidence?
- Are there unsupported or hallucinated claims?

3. Evaluation Criteria Alignment
- Does the proposal address the buyer's evaluation criteria?
- Are important evaluation points missing?

4. Win Theme Alignment
- Are the required win themes naturally incorporated?
- Are any win themes missing?

5. Proposal Quality
- Is the proposal clear?
- Is it persuasive?
- Is it technically accurate?

Return ONLY valid JSON using this exact structure:
{{
    "status": "PASS | FAIL",
    "score": 0,
    "feedback": [],
    "missing_requirements": [],
    "missing_win_themes": [],
    "missing_evaluation_criteria": [],
    "unsupported_claims": [],
    "improvement_suggestions": []
}}

Do not generate or rewrite proposal content.
Only review it.
"""
    )
])