from app.agents.Section_writer.services.mongo_services.mongo_services import ContextBuilder




async def context_builder_node(state):

    builder = ContextBuilder()

    context = builder.build_context(
        company_id=state["company_id"],
        tender_id=state["tender_id"],
       
    )

    return {
        "generation_context": context,
        "workflow_metadata": {
            **state["workflow_metadata"],
            "current_node": "context_builder",
            "workflow_status": "Completed",
        },
    }
