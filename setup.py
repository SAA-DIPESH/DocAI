import os

# Define folder structure
folders = [
    "app",
    "app/graph",
    "app/agents",
    "app/prompts",
    "app/models",
    "app/services",
    "app/utils",
    "app/output",
    "app/output/rewritten_constitution",
    "app/output/company_profiles",
    "app/output/specifications",
    "data",
    "data/constitutions",
    "data/company_docs",
    "tests"
]

# Define files to create
files = [
    "app/main.py",
    "app/graph/graph.py",
    "app/graph/state.py",
    "app/graph/nodes.py",
    "app/agents/constitution_agent.py",
    "app/agents/company_agent.py",
    "app/agents/specification_agent.py",
    "app/prompts/constitution_prompt.py",
    "app/prompts/company_prompt.py",
    "app/prompts/specification_prompt.py",
    "app/models/company_profile.py",
    "app/models/workflow_models.py",
    "app/services/document_loader.py",
    "app/services/extractor_service.py",
    "app/services/llm_service.py",
    "app/utils/helpers.py",
    "app/utils/logger.py",
    "requirements.txt",
    ".env",
    "README.md"
]

# Create folders
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"Created folder: {folder}")

# Create files
for file in files:
    with open(file, "w") as f:
        pass
    print(f"Created file: {file}")

print("\nProject structure created successfully!")