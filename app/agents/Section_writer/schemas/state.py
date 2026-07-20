import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict
 
# =====================================================
# Common Workflow Types
# =====================================================
 
WorkflowStatus = Literal[
    "Pending",
    "Running",
    "Completed",
    "Failed",
]
 
# =====================================================
# Common Workflow Metadata
# =====================================================
 
class WorkflowMetadata(TypedDict, total=False):
    workflow_status: WorkflowStatus
 
    current_node: str
    previous_node: Optional[str]
 
    started_at: Optional[str]
    completed_at: Optional[str]
 
    retry_count: int
 
    warnings: List[str]
    errors: List[str]
 
# =====================================================
# Proposal Generation State
# =====================================================



# class ProposalGenerationState(TypedDict, total=False):

#     company_id: str
#     tender_id: str
#     user_id: str

#     generation_context: Dict[str, Any]

#     generated_content: Dict[str, Any]

#     validation_result: Dict[str, Any]
#     compliance_result: Dict[str, Any]

#     improvement_feedback: list[str]

#     section_writer_token_usage: Dict[str, Any]
#     compliance_token_usage: Dict[str, Any]

#     section_results: Annotated[List[Dict[str, Any]], operator.add]

#     workflow_metadata: WorkflowMetadata

class ProposalGenerationState(TypedDict):

    company_id: str
    tender_id: str
    user_id: str
    is_regenerate: bool

    generation_context: dict

    workflow_metadata: dict

    section_results: Annotated[list, operator.add]
    
    
class SectionState(TypedDict):

    generation_context: dict

    validation_result: dict

    generated_content: dict

    compliance_result: dict

    section_writer_token_usage: dict

    compliance_token_usage: dict

    improvement_feedback: list

    section_results: list

    workflow_metadata: dict
