import asyncio

from DocAI.app.agents.tender_requirement_agent.services.requirement_service import RequirementService


async def main():

    service = RequirementService()

    result = await service.process_tender(
        company_id="6a44ded6d85cdcc9dc8fe0ec",
        tender_id="6a44e3f63b19bea856280095",
        user_id="user101",
        user_name="Dipesh",
        status="Regenerating",      # or "Active"
    )

    from pprint import pprint
    pprint(result)


if __name__ == "__main__":
    asyncio.run(main())