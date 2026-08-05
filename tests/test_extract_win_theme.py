from pprint import pprint

from app.agents.wintheam_generator.graph.nodes.wintheam_extract import (
    extract_win_theme_node,
)

state = {
    "request_id": "test-001",
    "company_id": "6a7091c7c104500e44abc1f5",
    "industry": "Technology Services",
    "cpv_codes": [
        "72000000",
        "79000000",
        "80000000",
    ],
    "warnings": [],
    "node_latencies": {},
}

result = extract_win_theme_node(state)

print("=" * 80)
print("FINAL RESULT")
print("=" * 80)

pprint(result)

print("=" * 80)
print("ANCHOR GROUPS")
print("=" * 80)

for anchor in result.get("anchor_groups", []):
    print(anchor["anchor_id"])