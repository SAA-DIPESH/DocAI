from langgraph.types import Send
from app.agents.Section_writer.schemas.state import ProposalGenerationState, SectionState
from langgraph.graph import END





# def route_sections(
#     state: ProposalGenerationState,
# ):

#     sends = []

#     for section in state["generation_context"]["Sections"]:

#         sends.append(
#             Send(
#                 "process_section",
#                 {
#                     **state,
#                     "section_id": section["SectionId"],
#                     "generation_context": {
#                         "Section": section,
#                         "WinThemes": state["generation_context"]["WinThemes"]
#                     }
#                 }
#             )
#         )

#     return sends





# MAX_RETRIES = 2

# def compliance_router(state: ProposalGenerationState):

#     compliance = state["compliance_result"]

#     status = compliance["status"]
#     score = compliance["score"]

#     retry_count = state.get("workflow_metadata", {}).get("retry_count", 0)

#     if status == "PASS" and score >= 70:
#         return END

#     if retry_count >= MAX_RETRIES:
#         return END

#     return "section_writer"

from langgraph.types import Send
from langgraph.graph import END

from app.agents.Section_writer.schemas.state import (
    ProposalGenerationState,
    SectionState,
)

MAX_RETRIES = 2


# def route_sections(state: ProposalGenerationState):

#     context = state["generation_context"]

#     return [
#         Send(
#             "validate_context",
#             {
#                 "generation_context": {
#                     "Section": section,
#                     "WinThemes": context["WinThemes"],
#                 },
#                 "workflow_metadata": {},
#             },
#         )
#         for section in context["Sections"]
#     ]

from langgraph.types import Send

def route_sections(state: ProposalGenerationState):
    context = state["generation_context"]
    sends = []

    for section in context["Sections"]:
        sends.append(
            Send(
                "process_section",   # <-- target the subgraph node, not "validate_context"
                {
                    "generation_context": {
                        "Section": section,
                        "WinThemes": context["WinThemes"],
                    },
                    "workflow_metadata": {},
                },
            )
        )

    return sends
def validation_router(state: SectionState):

    if state["validation_result"]["is_valid"]:
        return "section_writer"

    return "merge_section"


def compliance_router(state: SectionState):

    compliance = state["compliance_result"]

    status = compliance.get("status", "FAIL")
    score = compliance.get("score", 0)

    workflow = state.get("workflow_metadata", {})
    retry_count = workflow.get("retry_count", 0)

    if status == "PASS" and score >= 70:
        return "merge_section"

    if retry_count >= MAX_RETRIES:
        return "merge_section"

    workflow["retry_count"] = retry_count + 1

    return "section_writer"