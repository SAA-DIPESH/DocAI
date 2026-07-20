# Tender Section Planner

The Section Planner is a mandatory LLM agent with explicit OpenAI, NVIDIA Build,
and Mistral AI providers. Python loads and normalizes MongoDB inputs and sends a dynamic
hierarchy contract to the selected provider. The LLM creates tender-specific
group, section, and subsection names/descriptions and maps exact source IDs.
Python assigns stable structural IDs and owns priority, exact weights, evidence
flags, case-study flags, lineage, final assembly, validation, and persistence.

There is no deterministic plan-generation fallback and no automatic provider
fallback. The endpoint cannot return a successful plan without a valid response
ID from the explicitly selected provider.

The LLM structured-output model is `DynamicSectionPlannerLLMDecision`, not
`ProposalPlan`. Python joins complete source criteria (including exact stored
`WeightPercent`), builds traceability, assigns structural IDs, and assembles the
dynamic hierarchy deterministically.
Requirement Deduplication supplies `CanonicalRequirementId` directly; the legacy
`DeduplicatedRequirementId` field is not accepted. Every emitted section and
subsection contains at least one response-applicable canonical requirement.
Evaluation Criteria cannot activate nodes. Every section has at least one
requirement-backed subsection.

## Setup

```powershell
cd C:\Users\Admin\source\repos\SaaProjects\TenderSectionPlanner
python -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Configure at minimum:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=DocAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your-real-openai-api-key
OPENAI_MODEL=gpt-5.1
```

For NVIDIA Build instead:

```env
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=your-real-nvidia-api-key
NVIDIA_MODEL=meta/llama-3.3-70b-instruct
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

For Mistral AI instead:

```env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your-real-mistral-api-key
MISTRAL_MODEL=mistral-large-latest
MISTRAL_BASE_URL=https://api.mistral.ai/v1
MISTRAL_TIMEOUT_SECONDS=180
MISTRAL_MAX_RETRIES=2
MISTRAL_TEMPERATURE=0.2
```

NVIDIA Build uses its official OpenAI-compatible Chat Completions endpoint. The
provider is selected only through `LLM_PROVIDER`; failures never trigger an
automatic switch to another provider.

Never commit the populated `.env` file.

LLM requests use compact response-applicable requirement and criterion DTOs.
Configure the hard request/output budgets and single repair limit with:

```env
LLM_MAX_INPUT_TOKENS=12000
LLM_MAX_OUTPUT_TOKENS=3000
LLM_MAX_REPAIR_ATTEMPTS=1
```

Start the API:

```powershell
python -m uvicorn main:app --reload
```

Swagger is available at `http://127.0.0.1:8000/docs`.

The application fails startup when the selected provider's credentials/model are
absent or any of these instruction files is missing or empty:

- `Section_Planner_Constitution.md`
- `Section_Planner_Specification.md`
- `Section_Planner_User_Prompt.md`

MongoDB supplies Requirement Deduplication output from
`TenderRequirementDeduplications` and active completed Evaluation Criteria
output from `EvaluationCriteria`. Both records are scoped to the request's
`CompanyId` and `TenderId`. Tender Section Configuration is not loaded or used.

## Request

Send `POST /section-planner`:

```json
{
  "CompanyId": "company-1",
  "TenderId": "tender-1",
  "IsRegenerate": false,
  "UserId": "user-1",
  "UserName": "Jane Doe",
  "ProjectId": "project-1",
  "JwtToken": "runtime-only"
}
```

`JwtToken` is never sent to either provider, logged, or persisted. A successful persisted
result contains:

```json
{
  "PlanStatus": "Generated",
  "Status": "Active",
  "LLMMetadata": {
    "Provider": "OpenAI, NVIDIA Build, or Mistral AI",
    "Model": "configured-provider-model",
    "ResponseId": "resp_redacted",
    "PromptHashes": {
      "Constitution": "sha256_redacted",
      "Specification": "sha256_redacted",
      "UserPrompt": "sha256_redacted"
    },
    "InputRequirementCount": 1,
    "InputCriterionCount": 1,
    "RepairAttempts": 0,
    "Usage": {
      "InputTokens": 0,
      "OutputTokens": 0,
      "TotalTokens": 0
    }
  }
}
```

`LLMMetadata` remains inside MongoDB `JsonOutput` for internal cost/audit use.
The public POST response and `/section-planner/latest` DTO intentionally omit
`LLMMetadata`, token usage, prompt audit metadata, provider response IDs, and
`Validation.Warnings`/`Validation.Information`. Swagger exposes only this clean
public contract while retaining business `BlockingIssues`.

## Tests

```powershell
python -m pytest -q
python -m ruff check .
```

Unit tests use mocked OpenAI and NVIDIA clients and never make paid calls. A manual
integration smoke-test guard is enabled only when:

```env
RUN_OPENAI_INTEGRATION_TEST=true
```



## start the agent
python -m uvicorn main:app --host 127.0.0.1 --port 8550 --reload
