from app.agents.wintheam_extractor.graph.workflow import wintheam_extractor_graph




initial_state = {

    "company_id": "6a14671b840b868dfd6bdc75",
    "industry": "IT Services",
    "cpv_code": "72000000-5",

    "node_latencies": {}
}

result = wintheam_extractor_graph.invoke(initial_state)


print(result)
