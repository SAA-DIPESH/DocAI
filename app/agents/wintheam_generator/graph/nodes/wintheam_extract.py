import time
import requests
from typing import Dict, Any
import os
from dotenv import load_dotenv
from app.agents.wintheam_generator.graph.agent_state import WinThemeState


load_dotenv()


try:
    API_URL = os.getenv("WIN_THEME_GENERATOR_API_URL")

    if not API_URL:
        raise ValueError("WIN_THEME_GENERATOR_API_URL is empty.")

except Exception as e:
    raise RuntimeError(f"Configuration Error: {e}")
    
    

def extract_win_theme_node(state: WinThemeState) -> Dict[str, Any]:

    print("\n" + "=" * 80)
    print(">>> ENTER extract_win_theme_node")
    print("=" * 80)

    start = time.perf_counter()

    payload = {
        "company_id": state["company_id"],
        "industry": state["industry"],
        "cpv_code": state["cpv_code"],
    }

    print("Calling Extract API:", API_URL)
    print("Payload:", payload)

    try:
        response = requests.post(
            API_URL,
            json=payload,
        )

        print("Extract API Status Code:", response.status_code)

        response.raise_for_status()

        response_data = response.json()

        extractor_response = response_data.get("response", {})
        raw_anchor_groups = extractor_response.get("anchor_groups", [])

        print(f"Raw Anchor Groups: {len(raw_anchor_groups)}")

        anchor_groups = [
            {
                "anchor_id": f"ANCHOR_{index + 1:03d}",
                "objective": "Retrieve company evidence relevant to this capability area.",
                "anchor_query": " ".join(anchor_group.get("anchor_tags", [])),
                "anchor_tags": anchor_group.get("anchor_tags", []),
                "query_variants": anchor_group.get("query_variants", []),
            }
            for index, anchor_group in enumerate(raw_anchor_groups)
        ]

        print(f"Processed Anchor Groups: {len(anchor_groups)}")

        if anchor_groups:
            print("First Anchor:", anchor_groups[0])

        context = {
            "company_id": response_data.get("company_id", state["company_id"]),
            "cpv_code": response_data.get("cpv_code", state["cpv_code"]),
            "procurement_domain": extractor_response.get("procurement_domain"),
            "buyer_sector_context": extractor_response.get("buyer_sector_context"),
        }

        end = time.perf_counter()

        print(f"Extract Node Time: {round(end - start, 2)}s")
        print("<<< EXIT extract_win_theme_node")
        print("=" * 80)

        return {
            "context": context,
            "anchor_groups": anchor_groups,
            "current_anchor_index": 0,
            "generated_themes": [],
            "rules": state.get(
                "rules",
                {
                    "minimum_evidence_items": 2,
                    "minimum_distinct_documents": 2,
                },
            ),
            "next_step": "continue" if anchor_groups else "end",
            "status": "success" if anchor_groups else "insufficient_evidence",
            "validation_status": response_data.get("validation_status", "passed"),
            "current_step": "extract_win_theme",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "extract_win_theme": round(end - start, 3),
            },
        }

    except requests.exceptions.RequestException as e:

        end = time.perf_counter()

        print("EXTRACT NODE ERROR:", str(e))
        print("<<< EXIT extract_win_theme_node (FAILED)")
        print("=" * 80)

        return {
            "context": {},
            "anchor_groups": [],
            "current_anchor_index": 0,
            "generated_themes": [],
            "next_step": "end",
            "status": "failed",
            "validation_status": "failed",
            "current_step": "extract_win_theme",
            "error": str(e),
            "warnings": [str(e)],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "extract_win_theme": round(end - start, 3),
            },
        }