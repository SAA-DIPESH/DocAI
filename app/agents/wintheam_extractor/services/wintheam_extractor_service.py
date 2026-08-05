# app/agents/wintheam_extractor/services/wintheam_extractor_service.py

import uuid
from typing import Any, Dict, List

from app.agents.wintheam_extractor.graph.graph import (
    wintheam_extractor_graph,
)
from app.agents.wintheam_extractor.graph.agent_state import (
    WintheamState,
)


class WinThemeExtractorService:

    @staticmethod
    def create_initial_state(
        company_id: str,
        industry: str,
        cpv_codes: List[str],
    ) -> WintheamState:

        return {
            "request_id": str(uuid.uuid4()),

            "company_id": company_id,
            "industry": industry,
            "cpv_codes": cpv_codes,

            "retrieval_blueprint": None,
            "raw_llm_response": None,

            "validation_status": None,
            "validation_feedback": [],

            "retry_count": 0,
            "max_retries": 2,

            "current_step": None,
            "status": "pending",
            "error": None,

            "node_latencies": {},
        }

    @staticmethod
    def generate(
        company_id: str,
        industry: str,
        cpv_codes: List[str],
    ) -> Dict[str, Any]:

        state = WinThemeExtractorService.create_initial_state(
            company_id=company_id,
            industry=industry,
            cpv_codes=cpv_codes,
        )

        final_state = wintheam_extractor_graph.invoke(state)

        return final_state