# test_win_theme_workflow.py

from app.agents.wintheam_generator.graph.workflow import win_theme_graph


state = {
    "company_id": "6a14671b840b868dfd6bdc75",
    "industry": "IT Services",
    "cpv_code": "72000000-5",
    "rules": {
        "minimum_evidence_items": 2,
        "minimum_distinct_documents": 2,
    },
    "current_anchor_index": 0,
    "generated_themes": [],
    "warnings": [],
    "unsupported_claims_removed": [],
    "status": "pending",
    "current_step": None,
    "error": None,
    "node_latencies": {},
}

result = win_theme_graph.invoke(state)

print("\nFINAL STATUS:")
print(result.get("status"))

print("\nCURRENT STEP:")
print(result.get("current_step"))

print("\nERROR:")
print(result.get("error"))

print("\nANCHOR GROUPS COUNT:")
print(len(result.get("anchor_groups", [])))

print("\nGENERATED THEMES COUNT:")
print(len(result.get("generated_themes", [])))

print("\nGENERATED THEMES:")
for index, theme in enumerate(result.get("generated_themes", []), start=1):
    print(f"\n--- Theme {index} ---")
    print(theme)

print("\nNODE LATENCIES:")
print(result.get("node_latencies"))