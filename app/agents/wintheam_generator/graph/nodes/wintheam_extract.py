import os
import time
from typing import Any, Dict

import requests
from dotenv import load_dotenv

from app.agents.wintheam_generator.graph.agent_state import WinThemeState

load_dotenv()

API_URL = os.getenv("WIN_THEME_GENERATOR_API_URL")
if not API_URL:
    raise RuntimeError("WIN_THEME_GENERATOR_API_URL is not configured.")


DEFAULT_RULES = {
    "minimum_evidence_items": 2,
    "minimum_distinct_documents": 2,
}


def extract_win_theme_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Extract win theme anchor groups from the Win Theme Generator service.
    """

    start = time.perf_counter()

    payload = {
        "company_id": state["company_id"],
        "industry": state["industry"],
        "cpv_code": state["cpv_code"],
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()

        response_data = response.json()

        print("=" * 80)
        print("Extractor API Response:")
        print(response_data)
        print("=" * 80)

        extractor_response = response_data.get("response")

        if extractor_response is None:
            return {
                "context": {},
                "anchor_groups": [],
                "current_anchor_index": 0,
                "generated_themes": [],
                "next_step": "end",
                "status": "failed",
                "validation_status": response_data.get(
                    "validation_status",
                    "failed",
                ),
                "current_step": "extract_win_theme",
                "error": "Extractor returned no retrieval plan.",
                "warnings": response_data.get(
                    "validation_feedback",
                    ["Extractor returned response=None"],
                ),
                "node_latencies": {
                    **state.get("node_latencies", {}),
                    "extract_win_theme": round(
                        time.perf_counter() - start,
                        3,
                    ),
                },
            }

        raw_anchor_groups = extractor_response.get("anchor_groups", [])
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

        context = {
            "company_id": response_data.get(
                "company_id",
                state["company_id"],
            ),
            "cpv_code": response_data.get(
                "cpv_code",
                state["cpv_code"],
            ),
            "procurement_domain": extractor_response.get(
                "procurement_domain"
            ),
            "buyer_sector_context": extractor_response.get(
                "buyer_sector_context"
            ),
        }

        latency = round(time.perf_counter() - start, 3)

        return {
            "context": context,
            "anchor_groups": anchor_groups,
            "current_anchor_index": 0,
            "generated_themes": [],
            "rules": state.get("rules", DEFAULT_RULES),
            "next_step": (
                "continue"
                if anchor_groups
                else "end"
            ),
            "status": (
                "success"
                if anchor_groups
                else "insufficient_evidence"
            ),
            "validation_status": response_data.get(
                "validation_status",
                "passed",
            ),
            "current_step": "extract_win_theme",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "extract_win_theme": latency,
            },
        }

    except (requests.RequestException, ValueError) as e:
        latency = round(time.perf_counter() - start, 3)

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
            "warnings": [
                *state.get("warnings", []),
                str(e),
            ],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "extract_win_theme": latency,
            },
        }