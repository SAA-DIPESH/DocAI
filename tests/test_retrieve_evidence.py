
from pprint import pprint

from app.agents.wintheam_generator.graph.nodes.wintheam_extract import (
    extract_win_theme_node,
)
from app.agents.wintheam_generator.graph.nodes.retrieve_chunk import (
    retrieve_evidence_node,
)

# ------------------------------------------------------------------
# Initial State
# ------------------------------------------------------------------

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

# ------------------------------------------------------------------
# Step 1 - Generate Anchor Groups
# ------------------------------------------------------------------

extract_result = extract_win_theme_node(state)

print("=" * 80)
print("EXTRACT RESULT")
print("=" * 80)

print("Status:", extract_result["status"])
print("Anchors:", len(extract_result["anchor_groups"]))

# ------------------------------------------------------------------
# Step 2 - Select First Anchor
# ------------------------------------------------------------------

state.update(extract_result)

state["current_anchor_group"] = extract_result["anchor_groups"][0]

print("=" * 80)
print("CURRENT ANCHOR")
print("=" * 80)

pprint(state["current_anchor_group"])

# ------------------------------------------------------------------
# Step 3 - Retrieve Evidence
# ------------------------------------------------------------------

retrieve_result = retrieve_evidence_node(state)

print("=" * 80)
print("RETRIEVE RESULT")
print("=" * 80)

print("Retrieval Status :", retrieve_result["retrieval_status"])
print("Status           :", retrieve_result["status"])
print("Error            :", retrieve_result.get("error"))

print(
    "Retrieved Chunks :",
    retrieve_result.get("retrieved_chunks_count"),
)

print(
    "Reranked Chunks  :",
    retrieve_result.get("reranked_chunks_count"),
)

print(
    "Evidence Count   :",
    len(retrieve_result.get("current_evidence", [])),
)

print("=" * 80)
print("FIRST EVIDENCE")
print("=" * 80)

if retrieve_result.get("current_evidence"):
    pprint(retrieve_result["current_evidence"][0])
else:
    print("No evidence returned.")