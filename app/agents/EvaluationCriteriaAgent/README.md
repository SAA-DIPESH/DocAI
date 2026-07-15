# Evaluation Criteria Agent

## Purpose

Retrieves tender evidence from Qdrant, extracts grounded evaluation criteria with OpenAI, validates the structured response, and writes `Evaluation_Evidence.json`.

## Workflow

1. Validate Qdrant collection and vector configuration.
2. Retrieve, expand, rank, and deduplicate evidence.
3. Build the grounded LLM input.
4. Run structured OpenAI extraction.
5. Validate schema, source references, numeric values, and grounding.
6. Write the final JSON output.

## Structure

- `graph/`: workflow construction, nodes, and state.
- `services/`: retrieval, LLM, validation, and output services.
- `schemas/`: request and response types.
- `prompts/`: runtime prompt.
- `resources/`: constitution and output specification.
- `artifacts/`: optional debug outputs.

## Run

The original command remains supported:

```powershell
python evaluation_criteria_agent.py --company-id "<company-id>" --tender-id "<tender-id>"
```

Package execution is also available through the graph nodes module:

```powershell
python -m app.agents.evaluation_criteria.graph.nodes --company-id "<company-id>" --tender-id "<tender-id>"
```

## Environment

Copy `.env.example` to `.env` and configure OpenAI, Qdrant, vector names, retrieval mode, resource paths, and output paths. Never commit real credentials.
