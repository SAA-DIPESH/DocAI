# AI Agents

Multi-agent FastAPI project structure.
AI_Agents/
│
├── .gitignore
├── .env.example
├── requirements.txt
├── README.md                    # Project documentation
├── main.py                      # FastAPI entry point
│
├── app/
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py            # Registers all agent routes
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── agent1_route.py
│   │       ├── agent2_route.py
│   │       ├── agent3_route.py
│   │       ├── ...
│   │       └── agentN_route.py
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   │
│   │   ├── agent1/
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── graph/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── workflow.py
│   │   │   │   ├── nodes.py
│   │   │   │   └── agent_state.py
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   └── service.py
│   │   │   │
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── request.py
│   │   │   │   └── response.py
│   │   │   │
│   │   │   ├── prompts/
│   │   │   │   ├── system_prompt.md
│   │   │   │   └── user_prompt.md
│   │   │   │
│   │   │   ├── input_files/
│   │   │   │   ├── constitution.md
│   │   │   │   ├── specification.md
│   │   │   │   └── examples.json
│   │   │   │
│   │   │   └── utils/           # Optional (only if needed)
│   │   │       ├── __init__.py
│   │   │       └── helper.py
│   │   │
│   │   ├── agent2/
│   │   │   ├── README.md
│   │   │   ├── graph/
│   │   │   ├── services/
│   │   │   ├── schemas/
│   │   │   ├── prompts/
│   │   │   ├── input_files/
│   │   │   └── utils/
│   │   │
│   │   ├── agent3/
│   │   │   └── ...
│   │   │
│   │   └── agentN/
│   │       └── ...
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── load_llms.py
│   │   ├── logger.py
│   │   ├── qdrant_client.py
│   │   ├── database.py
│   │   └── secrets.py
│   │
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   ├── base_models.py
│   │   ├── base_state.py
│   │   └── base_response.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py
│       ├── file_loader.py
│       ├── markdown.py
│       ├── retry.py
│       ├── timer.py
│       └── validators.py
│
├── tests/
│   ├── __init__.py
│   ├── agent1/
│   ├── agent2/
│   ├── agent3/
│   └── shared/
│
├── logs/                        # Runtime logs (ignored by Git)
│
└── docs/                        # Optional
    ├── architecture.md
    ├── deployment.md
    └── api.md